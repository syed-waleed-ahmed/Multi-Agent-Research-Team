"""Integration tests for the staged pipeline using REAL CrewAI agents.

``litellm.completion`` is patched to return scripted responses through
LiteLLM's own ``mock_response`` / ``mock_tool_calls`` support, so the genuine
CrewAI agent loop, tool calling, our CallGuard, provider fallback and report
post-processing all execute — without any network access or API keys.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

pytest.importorskip("crewai")

import litellm  # noqa: E402

from research_team import crew  # noqa: E402
from research_team.config import AppConfig  # noqa: E402
from research_team.crew import ResearchOptions, ResearchResult, run_research_workflow  # noqa: E402
from research_team.exceptions import (  # noqa: E402
    RateLimitExceededError,
    WorkflowCancelledError,
)
from research_team.progress import EventType, RunControl  # noqa: E402
from research_team.search import SearchResult  # noqa: E402

SOURCE = SearchResult(
    "Official guide", "https://docs.example.org/guide", "Snippet", published="2026-01-01"
)
REPORT = (
    "# Title\n\n## Executive Summary\nSummary【1†https://docs.example.org/guide】\n\n"
    "## Key Findings\n- Unsourced [claim](https://made-up.example/x)\n\n"
    "```python\nprint('ok')\n```\n"
)


class FakeSearch:
    name = "fake-search"

    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, *, num_results: int) -> list[SearchResult]:
        self.queries.append(query)
        return [SOURCE]


class ScriptedLLM:
    """Routes each completion request to a scripted reply based on the prompt."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, fail_models: set[str] | None = None):
        self.real = litellm.completion
        self.calls: list[dict[str, Any]] = []
        self.fail_models = fail_models or set()
        monkeypatch.setattr(litellm, "completion", self)

    def __call__(self, **params: Any) -> Any:
        self.calls.append(params)
        if params["model"] in self.fail_models:
            raise litellm.RateLimitError(
                message="rate limited", llm_provider="groq", model=params["model"]
            )
        transcript = json.dumps(params["messages"])
        if "You are the Research Agent" in transcript:
            searched = any(m.get("role") == "tool" for m in params["messages"]) or (
                "Observation" in transcript
            )
            if not searched:
                return self._search_call(params)
            return self.real(
                **params, mock_response="## Overview\nNotes https://docs.example.org/guide"
            )
        if "You are the Coding / Analysis Agent" in transcript:
            return self.real(**params, mock_response="```python\nprint('hello')\n```")
        return self.real(**params, mock_response=REPORT)

    def _search_call(self, params: dict[str, Any]) -> Any:
        if params.get("tools"):
            return self.real(
                **params,
                mock_tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": "fake query"}),
                        },
                    }
                ],
            )
        return self.real(
            **params,
            mock_response=(
                'Thought: I should search.\nAction: web_search\nAction Input: {"query": "fake query"}'
            ),
        )


@pytest.fixture
def fake_search(monkeypatch):
    search = FakeSearch()
    monkeypatch.setattr(crew, "build_search_provider", lambda **_: search)
    return search


@pytest.fixture
def config():
    return AppConfig(groq_api_key="gk", serper_api_key="sk", max_retries=1, rate_limit_max_wait=5)


def test_full_pipeline_runs_three_real_agents(monkeypatch, fake_search, config):
    llm = ScriptedLLM(monkeypatch)
    events = []

    result = run_research_workflow(
        "Vector databases", config, ResearchOptions(depth="quick"), on_progress=events.append
    )

    assert isinstance(result, ResearchResult)
    # The real tool ran through our search abstraction and recorded the source.
    assert fake_search.queries == ["fake query"]
    assert [s.url for s in result.sources] == ["https://docs.example.org/guide"]
    assert result.search_queries == ("fake query",)
    # Citation markers were normalised and checked against retrieved sources.
    assert "【" not in result.report
    assert result.citation_check.matched == ["https://docs.example.org/guide"]
    assert result.citation_check.unmatched == ["https://made-up.example/x"]
    assert "print('hello')" in result.code_examples
    assert "## Research Methodology" in result.document
    assert "## Sources Retrieved During Research" in result.document
    assert result.model == "openai/gpt-oss-120b"
    assert result.provider == "Groq"
    # Credentials are passed explicitly to every request.
    assert all(call.get("api_key") == "gk" for call in llm.calls)

    types = [e.type for e in events]
    assert types[0] is EventType.RUN_STARTED and types[-1] is EventType.RUN_COMPLETED
    started = [e.stage.value for e in events if e.type is EventType.STAGE_STARTED]
    completed = [e.stage.value for e in events if e.type is EventType.STAGE_COMPLETED]
    assert started == completed == ["research", "coding", "synthesis"]
    assert any(e.type is EventType.SEARCH for e in events)


def test_rate_limit_falls_back_for_current_stage_only(monkeypatch, fake_search):
    config = AppConfig(
        groq_api_key="gk",
        serper_api_key="sk",
        max_retries=0,
        rate_limit_max_wait=0,
        fallback_providers=("openrouter",),
        openrouter_api_key="ok",
    )
    llm = ScriptedLLM(monkeypatch, fail_models={"groq/openai/gpt-oss-120b"})
    events = []

    result = run_research_workflow("Topic", config, on_progress=events.append)

    fallbacks = [e for e in events if e.type is EventType.PROVIDER_FALLBACK]
    assert len(fallbacks) == 1 and fallbacks[0].data["to"] == "openrouter"
    assert result.provider == "OpenRouter"
    # Research was retried on the fallback; nothing ran twice after that.
    started = [e.stage.value for e in events if e.type is EventType.STAGE_STARTED]
    assert started == ["research", "research", "coding", "synthesis"]
    groq_calls = [c for c in llm.calls if c["model"].startswith("groq/")]
    assert len(groq_calls) == 1  # max_retries=0: one attempt, no pipeline restart


def test_rate_limit_without_fallback_raises_typed_error(monkeypatch, fake_search, config):
    ScriptedLLM(monkeypatch, fail_models={"groq/openai/gpt-oss-120b"})
    monkeypatch.setattr("research_team.progress.RunControl.wait", lambda self, s: None)
    events = []
    with pytest.raises(RateLimitExceededError):
        run_research_workflow("Topic", config, on_progress=events.append)
    assert any(e.type is EventType.RETRY for e in events)
    assert events[-1].type is EventType.STAGE_FAILED


def test_cancelled_run_stops_before_next_request(monkeypatch, fake_search, config):
    llm = ScriptedLLM(monkeypatch)
    control = RunControl()

    def cancel_after_research(event):
        if event.type is EventType.STAGE_COMPLETED:
            control.cancel()

    with pytest.raises(WorkflowCancelledError):
        run_research_workflow("Topic", config, on_progress=cancel_after_research, control=control)
    transcripts = [json.dumps(c["messages"]) for c in llm.calls]
    assert not any("Coding / Analysis Agent" in t for t in transcripts)


def test_empty_topic_raises_value_error(base_config):
    with pytest.raises(ValueError):
        run_research_workflow("   ", base_config)


def test_invalid_options_raise_value_error(base_config):
    with pytest.raises(ValueError):
        run_research_workflow("topic", base_config, ResearchOptions(depth="infinite"))


def test_research_result_total_tokens():
    result = ResearchResult(
        topic="t", report="r", model="m", duration_seconds=1.0, token_usage={"total_tokens": 10}
    )
    assert result.total_tokens == 10
    assert (
        ResearchResult(topic="t", report="r", model="m", duration_seconds=1.0).total_tokens is None
    )


def test_manager_gets_larger_output_budget(monkeypatch, fake_search, config):
    llm = ScriptedLLM(monkeypatch)
    run_research_workflow("Topic", config)
    budgets = {}
    for call in llm.calls:
        transcript = json.dumps(call["messages"])
        stage = "synthesis" if "You are the Manager Agent" in transcript else "other"
        budgets.setdefault(stage, set()).add(call["max_tokens"])
    assert budgets["synthesis"] == {3072}
    assert budgets["other"] == {2048}


def test_manager_receives_actually_retrieved_sources(monkeypatch, fake_search, config):
    llm = ScriptedLLM(monkeypatch)
    run_research_workflow("Topic", config)
    synthesis = [
        json.dumps(c["messages"])
        for c in llm.calls
        if "You are the Manager Agent" in json.dumps(c["messages"])
    ]
    assert synthesis
    assert "Retrieved sources" in synthesis[0]
    assert "https://docs.example.org/guide" in synthesis[0]


def test_rate_limited_model_falls_back_to_another_groq_model(monkeypatch, fake_search):
    config = AppConfig(
        groq_api_key="gk",
        serper_api_key="sk",
        rate_limit_max_wait=0,
        fallback_providers=("groq:openai/gpt-oss-20b",),
    )
    ScriptedLLM(monkeypatch, fail_models={"groq/openai/gpt-oss-120b"})
    events = []

    result = run_research_workflow("Topic", config, on_progress=events.append)

    assert result.model == "openai/gpt-oss-20b"
    fallback = next(e for e in events if e.type is EventType.PROVIDER_FALLBACK)
    assert "openai/gpt-oss-20b" in fallback.message

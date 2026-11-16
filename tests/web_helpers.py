"""Helpers shared by the web tests: a scripted fake runner and app factory."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from research_team.config import AppConfig
from research_team.crew import ResearchResult
from research_team.progress import STAGES, EventType, ProgressEvent, Stage
from research_team.search import SearchResult
from research_team.web.app import create_app
from research_team.web.settings import WebSettings

SOURCE = SearchResult(
    "Docs", "https://docs.example.org/guide", "snippet", provider="serper", query="q"
)


class FakeRunner:
    """Emits realistic progress events; behaviour is controlled per test."""

    def __init__(
        self,
        *,
        error: BaseException | None = None,
        gate: threading.Event | None = None,
        on_call: Callable[[], None] | None = None,
    ) -> None:
        self.error = error
        self.gate = gate
        self.on_call = on_call
        self.calls: list[dict[str, Any]] = []

    def __call__(self, topic, config, options, *, on_progress, control, max_report_chars):
        self.calls.append(
            {"topic": topic, "options": options, "max_report_chars": max_report_chars}
        )
        if self.on_call:
            self.on_call()
        on_progress(ProgressEvent(EventType.RUN_STARTED, None, "Research run started"))
        for stage in STAGES:
            on_progress(
                ProgressEvent(EventType.STAGE_STARTED, stage, f"{stage.agent_name} started")
            )
            on_progress(ProgressEvent(EventType.LLM_CALL, stage, "Model request sent"))
            if stage is Stage.RESEARCH:
                on_progress(
                    ProgressEvent(
                        EventType.SEARCH, stage, "Searched: q", {"query": "q", "results": 1}
                    )
                )
                if self.gate is not None:
                    while not self.gate.wait(0.01):
                        control.check()
                if self.error is not None:
                    on_progress(
                        ProgressEvent(
                            EventType.STAGE_FAILED,
                            stage,
                            "stopped",
                            {"error_type": type(self.error).__name__},
                        )
                    )
                    raise self.error
            control.check()
            on_progress(ProgressEvent(EventType.STAGE_COMPLETED, stage, f"{stage.agent_name} done"))
        on_progress(ProgressEvent(EventType.RUN_COMPLETED, None, "Report ready"))
        return ResearchResult(
            topic=topic,
            report="# Report\n\n[docs](https://docs.example.org/guide)",
            model=options.model,
            duration_seconds=0.01,
            token_usage={"total_tokens": 99},
            provider="Groq",
            research_notes="notes",
            code_examples="code",
            sources=(SOURCE,),
            search_queries=("q",),
            methodology="## Research Methodology",
            document="# Report\n\n---\n\n## Sources Retrieved During Research",
        )


def make_settings(**overrides: Any) -> WebSettings:
    values: dict[str, Any] = {
        "database_url": "sqlite://",
        "static_dir": None,
        "ip_hash_salt": "test-salt",
        "result_cache_ttl_hours": 0,
    }
    values.update(overrides)
    return WebSettings(**values)


def make_app(runner: FakeRunner | None = None, *, config: AppConfig | None = None, **settings: Any):
    return create_app(
        make_settings(**settings),
        config=config or AppConfig(groq_api_key="gk", serper_api_key="sk"),
        runner=runner or FakeRunner(),
    )


def wait_for_status(client, job_id: str, statuses: set[str], timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/api/v1/research/{job_id}/status").json()
        if body["status"] in statuses:
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never reached {statuses}; last={body['status']}")

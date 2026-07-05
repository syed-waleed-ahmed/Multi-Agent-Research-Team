"""Tests for workflow orchestration: retries, result extraction, error mapping.

These tests never touch CrewAI or the network; the crew is stubbed.
"""

from __future__ import annotations

import pytest

from research_team import crew
from research_team.crew import ResearchResult
from research_team.exceptions import RateLimitExceededError, WorkflowError


class _FakeUsage:
    def model_dump(self):
        return {"total_tokens": 123, "prompt_tokens": 100, "completion_tokens": 23}


class _FakeOutput:
    def __init__(self, raw="# Report\n\nBody.", usage=None):
        self.raw = raw
        self.token_usage = usage


# --------------------------------------------------------------------------- #
# ResearchResult
# --------------------------------------------------------------------------- #
def test_research_result_total_tokens():
    result = ResearchResult(
        topic="t",
        report="r",
        model="m",
        duration_seconds=1.0,
        token_usage={"total_tokens": 10},
    )
    assert result.total_tokens == 10


def test_research_result_total_tokens_missing():
    result = ResearchResult(topic="t", report="r", model="m", duration_seconds=1.0)
    assert result.total_tokens is None


# --------------------------------------------------------------------------- #
# Extraction helpers
# --------------------------------------------------------------------------- #
def test_extract_report_prefers_raw():
    assert crew._extract_report(_FakeOutput(raw="  hello  ")) == "hello"


def test_extract_report_empty_raises():
    class Empty:
        raw = ""

        def __str__(self):
            return ""

    with pytest.raises(WorkflowError):
        crew._extract_report(Empty())


def test_extract_token_usage_from_model_dump():
    usage = crew._extract_token_usage(_FakeOutput(usage=_FakeUsage()))
    assert usage["total_tokens"] == 123


def test_extract_token_usage_none():
    assert crew._extract_token_usage(_FakeOutput(usage=None)) == {}


# --------------------------------------------------------------------------- #
# Retry logic
# --------------------------------------------------------------------------- #
def test_retry_succeeds_after_transient(monkeypatch):
    monkeypatch.setattr(crew, "_transient_error_types", lambda: (ValueError,))
    monkeypatch.setattr(crew, "_rate_limit_error_type", lambda: None)
    calls = {"n": 0}

    def action():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    result = crew._run_with_retries(action, max_retries=3, sleep=lambda *_: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_exhausted_raises_workflow_error(monkeypatch):
    monkeypatch.setattr(crew, "_transient_error_types", lambda: (ValueError,))
    monkeypatch.setattr(crew, "_rate_limit_error_type", lambda: None)

    def action():
        raise ValueError("always")

    with pytest.raises(WorkflowError):
        crew._run_with_retries(action, max_retries=2, sleep=lambda *_: None)


def test_rate_limit_translated(monkeypatch):
    class FakeRateLimit(Exception):
        pass

    monkeypatch.setattr(crew, "_transient_error_types", lambda: (FakeRateLimit,))
    monkeypatch.setattr(crew, "_rate_limit_error_type", lambda: FakeRateLimit)

    def action():
        raise FakeRateLimit("429")

    with pytest.raises(RateLimitExceededError):
        crew._run_with_retries(action, max_retries=1, sleep=lambda *_: None)


def test_unexpected_error_wrapped(monkeypatch):
    monkeypatch.setattr(crew, "_transient_error_types", lambda: ())

    def action():
        raise RuntimeError("boom")

    with pytest.raises(WorkflowError):
        crew._run_with_retries(action, max_retries=3, sleep=lambda *_: None)


# --------------------------------------------------------------------------- #
# End-to-end workflow (crew stubbed)
# --------------------------------------------------------------------------- #
def test_empty_topic_raises_value_error(base_config):
    with pytest.raises(ValueError):
        crew.run_research_workflow("   ", base_config)


def test_run_workflow_happy_path(monkeypatch, base_config):
    class FakeCrew:
        def kickoff(self, inputs):
            assert inputs == {"topic": "quantum computing"}
            return _FakeOutput(raw="# Final", usage=_FakeUsage())

    monkeypatch.setattr(crew, "build_crew", lambda topic, config: FakeCrew())

    result = crew.run_research_workflow("quantum computing", base_config)

    assert isinstance(result, ResearchResult)
    assert result.report == "# Final"
    assert result.topic == "quantum computing"
    assert result.model == base_config.groq_model
    assert result.total_tokens == 123
    assert result.duration_seconds >= 0.0

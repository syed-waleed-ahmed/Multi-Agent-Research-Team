"""Tests for provider resolution and the per-call retry guard."""

from __future__ import annotations

import pytest

from research_team.config import AppConfig
from research_team.exceptions import (
    ConfigError,
    ProviderUnavailableError,
    RateLimitExceededError,
    WorkflowCancelledError,
)
from research_team.progress import EventType, RunControl, Stage
from research_team.providers import CallGuard, provider_spec, resolve_providers


class Transient(Exception):
    pass


class RateLimited(Transient):
    def __init__(self, retry_after: str | None = None):
        super().__init__("429")
        headers = {"retry-after": retry_after} if retry_after else {}
        self.response = type("R", (), {"headers": headers})()


class Fatal(Exception):
    pass


class FakeControl(RunControl):
    """RunControl whose waits are recorded instead of slept."""

    def __init__(self):
        super().__init__()
        self.waits: list[float] = []

    def wait(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.check()


def _guard(control=None, events=None, max_retries=3, rng=lambda: 1.0, rate_limit_budget=60.0):
    return CallGuard(
        rate_limit_budget=rate_limit_budget,
        control=control or FakeControl(),
        max_retries=max_retries,
        on_progress=(events.append if events is not None else None),
        provider="TestProvider",
        base_delay=2.0,
        max_delay=60.0,
        rng=rng,
        transient=(Transient,),
        rate_limit=RateLimited,
        fatal=(Fatal,),
    )


# --------------------------------------------------------------------------- #
# CallGuard
# --------------------------------------------------------------------------- #
def test_retries_only_the_failed_call_then_succeeds():
    control, events = FakeControl(), []
    guard = _guard(control, events)
    guard.stage = Stage.RESEARCH
    attempts = {"n": 0}

    def call():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise Transient("boom")
        return "ok"

    assert guard.run(call) == "ok"
    assert attempts["n"] == 3
    # rng=1.0 -> full exponential delay: 2s then 4s.
    assert control.waits == [2.0, 4.0]
    retries = [e for e in events if e.type is EventType.RETRY]
    assert [e.data["attempt"] for e in retries] == [1, 2]
    assert all(e.stage is Stage.RESEARCH for e in events)
    assert guard.calls == 3


def test_jitter_stays_within_half_to_full_delay():
    low = _guard(rng=lambda: 0.0).delay_for(3)
    high = _guard(rng=lambda: 1.0).delay_for(3)
    assert low == pytest.approx(4.0)  # 8s * 0.5
    assert high == pytest.approx(8.0)


def test_delay_is_capped():
    assert _guard(rng=lambda: 1.0).delay_for(20) == 60.0


def test_retry_after_header_is_honoured():
    guard = _guard(rng=lambda: 0.0)
    assert guard.delay_for(1, RateLimited(retry_after="17")) == 17.0
    # Never above the cap even if the provider asks for longer.
    assert guard.delay_for(1, RateLimited(retry_after="999")) == 60.0


def test_rate_limits_are_retried_within_a_time_budget():
    control = FakeControl()
    guard = _guard(control, rate_limit_budget=5)  # rng=1.0 -> delays 2s, 4s, ...

    def call():
        raise RateLimited()

    with pytest.raises(RateLimitExceededError):
        guard.run(call)
    assert control.waits == [2.0]  # waiting 4s more would exceed the 5s budget
    assert guard.calls == 2


def test_rate_limits_are_not_bound_by_max_retries():
    control = FakeControl()
    guard = _guard(control, max_retries=0, rate_limit_budget=60)
    attempts = {"n": 0}

    def call():
        attempts["n"] += 1
        if attempts["n"] < 4:
            raise RateLimited()
        return "ok"

    assert guard.run(call) == "ok"
    assert control.waits == [2.0, 4.0, 8.0]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Rate limit reached. Please try again in 7.66s. Visit ...", 7.66),
        ("Please try again in 1m2.5s.", 62.5),
        ("please TRY AGAIN IN 520ms", 0.52),
        ("rate limited", None),
    ],
)
def test_retry_hint_is_parsed_from_provider_message(message, expected):
    from research_team.providers import _retry_after_seconds

    result = _retry_after_seconds(Exception(message))
    assert result == (pytest.approx(expected) if expected is not None else None)


def test_message_hint_extends_the_backoff():
    class HintedRateLimit(RateLimited):
        def __str__(self):
            return "Please try again in 7.66s."

    assert _guard(rng=lambda: 0.0).delay_for(1, HintedRateLimit()) == pytest.approx(7.66)


def test_exhausted_transient_becomes_provider_unavailable():
    with pytest.raises(ProviderUnavailableError):
        _guard(max_retries=1).run(lambda: (_ for _ in ()).throw(Transient("down")))


def test_fatal_errors_are_not_retried():
    guard = _guard()
    with pytest.raises(ProviderUnavailableError) as exc:
        guard.run(lambda: (_ for _ in ()).throw(Fatal("model_not_found")))
    assert guard.calls == 1
    assert "invalid API key or unavailable model" in exc.value.public_message


def test_unexpected_errors_propagate_untouched():
    # e.g. context-window errors must reach CrewAI's own handling unchanged.
    with pytest.raises(KeyError):
        _guard().run(lambda: {}["missing"])


def test_cancellation_is_checked_before_each_call():
    control = FakeControl()
    control.cancel()
    called = []
    with pytest.raises(WorkflowCancelledError):
        _guard(control).run(lambda: called.append(1))
    assert called == []


# --------------------------------------------------------------------------- #
# Provider resolution
# --------------------------------------------------------------------------- #
def test_resolve_primary_with_model_override(base_config):
    specs = resolve_providers(base_config, "openai/gpt-oss-20b")
    assert [s.name for s in specs] == ["groq"]
    assert specs[0].litellm_model == "groq/openai/gpt-oss-20b"
    assert specs[0].api_key == "test-groq-key"


def test_same_provider_model_fallback():
    """Free-tier token limits are per model, so another Groq model is a real fallback."""
    config = AppConfig(
        groq_api_key="gk",
        serper_api_key="sk",
        fallback_providers=("groq:openai/gpt-oss-20b", "groq:openai/gpt-oss-120b"),
    )
    specs = resolve_providers(config)
    assert [(s.name, s.model) for s in specs] == [
        ("groq", "openai/gpt-oss-120b"),
        ("groq", "openai/gpt-oss-20b"),  # the duplicate of the primary is skipped
    ]
    assert specs[1].litellm_model == "groq/openai/gpt-oss-20b"


def test_fallbacks_without_credentials_are_skipped():
    config = AppConfig(
        groq_api_key="gk",
        serper_api_key="sk",
        fallback_providers=("gemini", "openrouter", "groq"),
        openrouter_api_key="ok",
    )
    specs = resolve_providers(config)
    assert [s.name for s in specs] == ["groq", "openrouter"]


def test_provider_spec_repr_hides_credentials(base_config):
    assert "test-groq-key" not in repr(provider_spec("groq", base_config))


def test_provider_spec_requires_credentials(base_config):
    with pytest.raises(ConfigError):
        provider_spec("gemini", base_config)


def test_openai_compatible_and_ollama_specs():
    config = AppConfig(
        llm_provider="openai_compatible",
        openai_compatible_base_url="http://localhost:1234/v1",
        openai_compatible_model="local-model",
        serper_api_key="sk",
    )
    spec = provider_spec("openai_compatible", config)
    assert spec.litellm_model == "openai/local-model"
    assert spec.base_url == "http://localhost:1234/v1"
    ollama = provider_spec("ollama", config)
    assert ollama.litellm_model == "ollama/llama3.1"
    assert ollama.api_key is None


# --------------------------------------------------------------------------- #
# LLM construction (real CrewAI objects, no network)
# --------------------------------------------------------------------------- #
def test_build_llm_passes_explicit_credentials(base_config, monkeypatch):
    pytest.importorskip("crewai")
    from research_team.providers import build_llm

    # A different key in the environment must NOT override the configured one.
    monkeypatch.setenv("GROQ_API_KEY", "env-key-should-be-ignored")
    llm = build_llm(provider_spec("groq", base_config), base_config)

    assert llm.api_key == "test-groq-key"
    assert llm.is_litellm is True
    assert llm.model == "groq/openai/gpt-oss-120b"
    assert llm.reasoning_effort == "low"


def test_guard_trips_after_terminal_error_until_next_stage():
    guard = _guard(max_retries=0, rate_limit_budget=0)
    calls = []

    def call():
        calls.append(1)
        raise RateLimited()

    with pytest.raises(RateLimitExceededError):
        guard.run(call)
    # CrewAI may re-invoke the LLM after an error: no new provider request is made.
    with pytest.raises(RateLimitExceededError):
        guard.run(call)
    assert len(calls) == 1
    guard.stage = Stage.CODING
    assert guard.run(lambda: "ok") == "ok"

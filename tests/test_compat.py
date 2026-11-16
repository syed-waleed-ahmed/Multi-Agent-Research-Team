"""Tests for third-party compatibility shims."""

from __future__ import annotations

import pytest

pytest.importorskip("crewai")

from research_team.compat import (  # noqa: E402
    configure_crewai_console,
    patch_litellm_cache_breakpoint,
)


@pytest.fixture(autouse=True)
def _dummy_groq_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key-for-construction")


def test_shim_strips_cache_breakpoint_marker():
    assert patch_litellm_cache_breakpoint() is True

    from crewai.llm import LLM

    llm = LLM(model="groq/openai/gpt-oss-20b", is_litellm=True)
    formatted = llm._format_messages_for_provider(
        [
            {"role": "system", "content": "stable", "cache_breakpoint": True},
            {"role": "user", "content": "hello", "cache_breakpoint": True},
        ]
    )

    assert formatted  # messages preserved
    assert all("cache_breakpoint" not in message for message in formatted)
    assert [m["content"] for m in formatted] == ["stable", "hello"]


def test_shim_is_idempotent():
    assert patch_litellm_cache_breakpoint() is True
    # A second call must not double-wrap or raise.
    assert patch_litellm_cache_breakpoint() is True


def test_console_formatter_follows_verbose_flag():
    from crewai.events.event_listener import event_listener

    try:
        assert configure_crewai_console(verbose=False) is True
        assert event_listener.formatter.verbose is False
        assert configure_crewai_console(verbose=True) is True
        assert event_listener.formatter.verbose is True
    finally:
        configure_crewai_console(verbose=False)

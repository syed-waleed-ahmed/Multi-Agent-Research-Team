"""Shared pytest fixtures.

Tests are written to run *without* network access or real API keys. Heavy
CrewAI code paths are mocked; only the crewai-gated tests in
``test_agents_tasks.py`` construct real CrewAI objects (and still make no
network calls).
"""

from __future__ import annotations

import pytest

from research_team.config import AppConfig


@pytest.fixture
def base_config() -> AppConfig:
    """A minimal, valid configuration suitable for unit tests."""
    return AppConfig(groq_api_key="test-groq-key", serper_api_key="test-serper-key")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all recognized environment variables for deterministic parsing."""
    for name in (
        "GROQ_API_KEY",
        "SERPER_API_KEY",
        "GROQ_MODEL",
        "GROQ_TEMPERATURE",
        "GROQ_MAX_TOKENS",
        "GROQ_MAX_RETRIES",
        "MAX_RPM",
        "REQUEST_TIMEOUT",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)
    # Ensure `.env` on disk never leaks into these tests.
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)

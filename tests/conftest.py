"""Shared pytest fixtures.

Tests run *without* network access or real API keys:

* pure-Python units (config, retries, search parsing, report checks, rate
  limits, repository) need nothing external;
* CrewAI-gated tests build real CrewAI objects and drive the real agent loop
  with ``litellm.completion`` patched to scripted responses (``fake_llm``);
* web tests run the real FastAPI app on an in-memory SQLite database with an
  injected fake runner.
"""

from __future__ import annotations

import pytest

from research_team.config import AppConfig

ENV_VARS = (
    "GROQ_API_KEY",
    "SERPER_API_KEY",
    "TAVILY_API_KEY",
    "GROQ_MODEL",
    "GROQ_TEMPERATURE",
    "GROQ_MAX_TOKENS",
    "GROQ_MAX_RETRIES",
    "MAX_RPM",
    "REQUEST_TIMEOUT",
    "WORKFLOW_TIMEOUT",
    "LOG_LEVEL",
    "LLM_PROVIDER",
    "LLM_FALLBACK_PROVIDERS",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_MODEL",
    "REASONING_EFFORT",
    "SEARCH_PROVIDERS",
)


@pytest.fixture
def base_config() -> AppConfig:
    """A minimal, valid configuration suitable for unit tests."""
    return AppConfig(groq_api_key="test-groq-key", serper_api_key="test-serper-key")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all recognized environment variables for deterministic parsing."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # Ensure `.env` on disk never leaks into these tests.
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)

"""Tests for configuration parsing and validation."""

from __future__ import annotations

import pytest

from research_team.config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    AppConfig,
)
from research_team.exceptions import ConfigError


def test_from_env_uses_defaults_for_optional_values(monkeypatch, clean_env):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")

    cfg = AppConfig.from_env(load_dotenv_file=False)

    assert cfg.groq_api_key == "gk"
    assert cfg.serper_api_key == "sk"
    assert cfg.groq_model == DEFAULT_GROQ_MODEL == "openai/gpt-oss-120b"
    assert cfg.temperature == DEFAULT_TEMPERATURE
    assert cfg.max_tokens == DEFAULT_MAX_TOKENS
    assert cfg.max_rpm is None
    assert cfg.request_timeout is None
    assert cfg.llm_provider == "groq"
    assert cfg.fallback_providers == ()
    assert cfg.search_providers == ("serper", "tavily")


def test_from_env_reads_overrides(monkeypatch, clean_env):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("GROQ_TEMPERATURE", "0.7")
    monkeypatch.setenv("GROQ_MAX_TOKENS", "2048")
    monkeypatch.setenv("MAX_RPM", "30")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDERS", "Gemini, openrouter")
    monkeypatch.setenv("LOG_LEVEL", "warning")

    cfg = AppConfig.from_env(load_dotenv_file=False)

    assert cfg.groq_model == "openai/gpt-oss-20b"
    assert cfg.temperature == 0.7
    assert cfg.max_tokens == 2048
    assert cfg.max_rpm == 30
    assert cfg.fallback_providers == ("gemini", "openrouter")
    assert cfg.normalized_log_level == "WARNING"


def test_missing_api_keys_raise_config_error(monkeypatch, clean_env):
    with pytest.raises(ConfigError) as exc:
        AppConfig.from_env(load_dotenv_file=False)
    message = str(exc.value)
    assert "GROQ_API_KEY" in message
    assert "SERPER_API_KEY" in message


def test_tavily_alone_satisfies_search_requirement():
    cfg = AppConfig(groq_api_key="gk", tavily_api_key="tk")
    assert cfg.serper_api_key == ""


def test_non_groq_provider_does_not_require_groq_key():
    cfg = AppConfig(llm_provider="gemini", gemini_api_key="g", serper_api_key="sk")
    assert cfg.missing_credentials("gemini") is None
    assert cfg.missing_credentials("groq") == "GROQ_API_KEY is required."


def test_non_numeric_temperature_raises(monkeypatch, clean_env):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")
    monkeypatch.setenv("GROQ_TEMPERATURE", "hot")

    with pytest.raises(ConfigError):
        AppConfig.from_env(load_dotenv_file=False)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature": 5.0},
        {"temperature": -1.0},
        {"max_tokens": 0},
        {"max_retries": -1},
        {"max_rpm": 0},
        {"request_timeout": 0},
        {"workflow_timeout": 0},
        {"groq_model": "   "},
        {"log_level": "LOUD"},
        {"reasoning_effort": "extreme"},
        {"llm_provider": "skynet"},
        {"fallback_providers": ("nope",)},
        {"fallback_providers": ("groq:",)},
        {"fallback_providers": ("skynet:some-model",)},
        {"rate_limit_max_wait": -1},
        {"search_providers": ("bing",)},
        {"llm_provider": "openai_compatible"},  # base URL + model missing
    ],
)
def test_invalid_values_raise(kwargs):
    with pytest.raises(ConfigError):
        AppConfig(groq_api_key="gk", serper_api_key="sk", **kwargs)


def test_with_overrides_ignores_none_and_applies_values(base_config):
    updated = base_config.with_overrides(temperature=0.9, groq_model=None)

    assert updated.temperature == 0.9
    assert updated.groq_model == base_config.groq_model
    # Original is unchanged (frozen / immutable).
    assert base_config.temperature == DEFAULT_TEMPERATURE


def test_with_overrides_without_changes_returns_same_instance(base_config):
    assert base_config.with_overrides(temperature=None) is base_config


def test_with_overrides_revalidates(base_config):
    with pytest.raises(ConfigError):
        base_config.with_overrides(temperature=9.0)

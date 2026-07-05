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
    assert cfg.groq_model == DEFAULT_GROQ_MODEL
    assert cfg.temperature == DEFAULT_TEMPERATURE
    assert cfg.max_tokens == DEFAULT_MAX_TOKENS
    assert cfg.max_rpm is None
    assert cfg.request_timeout is None


def test_from_env_reads_overrides(monkeypatch, clean_env):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GROQ_TEMPERATURE", "0.7")
    monkeypatch.setenv("GROQ_MAX_TOKENS", "2048")
    monkeypatch.setenv("MAX_RPM", "30")

    cfg = AppConfig.from_env(load_dotenv_file=False)

    assert cfg.groq_model == "llama-3.3-70b-versatile"
    assert cfg.temperature == 0.7
    assert cfg.max_tokens == 2048
    assert cfg.max_rpm == 30


def test_missing_api_keys_raise_config_error(monkeypatch, clean_env):
    with pytest.raises(ConfigError) as exc:
        AppConfig.from_env(load_dotenv_file=False)
    message = str(exc.value)
    assert "GROQ_API_KEY" in message
    assert "SERPER_API_KEY" in message


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
        {"groq_model": "   "},
    ],
)
def test_out_of_range_values_raise(kwargs):
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

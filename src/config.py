# src/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from crewai import LLM
from crewai_tools import SerperDevTool
from dotenv import load_dotenv

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 1024


@dataclass(frozen=True)
class AppConfig:
    groq_api_key: str
    serper_api_key: str
    groq_model: str = DEFAULT_GROQ_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS


def _parse_float(value: str | None, default: float, name: str) -> float:
    if value is None or not value.strip():
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid number.") from exc


def _parse_int(value: str | None, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid integer.") from exc


def load_config() -> AppConfig:
    load_dotenv()

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
    groq_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    temperature = _parse_float(os.getenv("GROQ_TEMPERATURE"), DEFAULT_TEMPERATURE, "GROQ_TEMPERATURE")
    max_tokens = _parse_int(os.getenv("GROQ_MAX_TOKENS"), DEFAULT_MAX_TOKENS, "GROQ_MAX_TOKENS")

    missing = []
    if not groq_api_key:
        missing.append("GROQ_API_KEY")
    if not serper_api_key:
        missing.append("SERPER_API_KEY")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing) + "."
        )

    return AppConfig(
        groq_api_key=groq_api_key,
        serper_api_key=serper_api_key,
        groq_model=groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return load_config()


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    config = get_config()
    os.environ.setdefault("GROQ_API_KEY", config.groq_api_key)
    return LLM(
        model=f"groq/{config.groq_model}",
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


@lru_cache(maxsize=1)
def get_web_search_tool() -> SerperDevTool:
    config = get_config()
    os.environ.setdefault("SERPER_API_KEY", config.serper_api_key)
    return SerperDevTool()

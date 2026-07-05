"""Runtime configuration and lazy factories for the LLM and web-search tool.

Design notes
------------
* Configuration is immutable (:class:`AppConfig` is a frozen dataclass) and is
  validated at construction time, so an invalid configuration fails fast with a
  clear :class:`~research_team.exceptions.ConfigError`.
* Heavy third-party imports (CrewAI, LiteLLM via CrewAI's ``LLM``) are performed
  lazily *inside* the factory functions. This keeps ``--help``/``--version`` and
  unit tests fast, and lets this module be imported without the full agent stack
  installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from .exceptions import ConfigError

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids importing heavy deps
    from crewai import LLM
    from crewai_tools import SerperDevTool

# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #
# Default model. llama-3.3-70b-versatile is chosen because it reliably completes
# the full three-agent workflow within Groq's free-tier per-minute token limit
# and produces higher-quality synthesis. For faster/cheaper runs set
# GROQ_MODEL=llama-3.1-8b-instant (note its lower free-tier TPM limit).
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 1024
DEFAULT_MAX_RETRIES = 3
DEFAULT_LOG_LEVEL = "INFO"

# Guard rails so that misconfiguration is caught before an API call is ever made.
_MAX_TEMPERATURE = 2.0
_MAX_REASONABLE_TOKENS = 200_000


@dataclass(frozen=True)
class AppConfig:
    """Immutable, validated application configuration.

    Instances are typically created via :meth:`from_env`, but may also be built
    directly (useful for tests or for embedding the workflow in another system).
    """

    groq_api_key: str
    serper_api_key: str
    groq_model: str = DEFAULT_GROQ_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    max_retries: int = DEFAULT_MAX_RETRIES
    # Optional operational guard rails for larger / long-running deployments.
    max_rpm: int | None = None
    request_timeout: int | None = None
    log_level: str = DEFAULT_LOG_LEVEL
    verbose: bool = False

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        errors: list[str] = []
        if not self.groq_api_key:
            errors.append("GROQ_API_KEY is required.")
        if not self.serper_api_key:
            errors.append("SERPER_API_KEY is required.")
        if not self.groq_model.strip():
            errors.append("GROQ_MODEL must not be empty.")
        if not 0.0 <= self.temperature <= _MAX_TEMPERATURE:
            errors.append(f"GROQ_TEMPERATURE must be between 0.0 and {_MAX_TEMPERATURE}.")
        if not 1 <= self.max_tokens <= _MAX_REASONABLE_TOKENS:
            errors.append(f"GROQ_MAX_TOKENS must be between 1 and {_MAX_REASONABLE_TOKENS}.")
        if self.max_retries < 0:
            errors.append("GROQ_MAX_RETRIES must be zero or greater.")
        if self.max_rpm is not None and self.max_rpm < 1:
            errors.append("MAX_RPM must be a positive integer when set.")
        if self.request_timeout is not None and self.request_timeout < 1:
            errors.append("REQUEST_TIMEOUT must be a positive integer when set.")
        if errors:
            raise ConfigError(" ".join(errors))

    def with_overrides(self, **overrides: Any) -> AppConfig:
        """Return a copy of this config with the given fields replaced.

        ``None`` values are ignored so callers can pass optional CLI overrides
        without having to branch on which flags were provided.
        """
        cleaned: dict[str, Any] = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **cleaned) if cleaned else self

    @classmethod
    def from_env(cls, *, load_dotenv_file: bool = True) -> AppConfig:
        """Build configuration from environment variables (and optional ``.env``)."""
        if load_dotenv_file:
            from dotenv import load_dotenv

            load_dotenv()

        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
            serper_api_key=os.getenv("SERPER_API_KEY", "").strip(),
            groq_model=(os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL),
            temperature=_parse_float(
                os.getenv("GROQ_TEMPERATURE"), DEFAULT_TEMPERATURE, "GROQ_TEMPERATURE"
            ),
            max_tokens=_parse_int(
                os.getenv("GROQ_MAX_TOKENS"), DEFAULT_MAX_TOKENS, "GROQ_MAX_TOKENS"
            ),
            max_retries=_parse_int(
                os.getenv("GROQ_MAX_RETRIES"), DEFAULT_MAX_RETRIES, "GROQ_MAX_RETRIES"
            ),
            max_rpm=_parse_optional_int(os.getenv("MAX_RPM"), "MAX_RPM"),
            request_timeout=_parse_optional_int(os.getenv("REQUEST_TIMEOUT"), "REQUEST_TIMEOUT"),
            log_level=(os.getenv("LOG_LEVEL", "").strip() or DEFAULT_LOG_LEVEL),
        )


# --------------------------------------------------------------------------- #
# Parsing helpers (pure functions, trivially unit-testable)
# --------------------------------------------------------------------------- #
def _parse_float(value: str | None, default: float, name: str) -> float:
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a valid number.") from exc


def _parse_int(value: str | None, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a valid integer.") from exc


def _parse_optional_int(value: str | None, name: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a valid integer.") from exc


# --------------------------------------------------------------------------- #
# Cached default configuration
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the process-wide default configuration built from the environment."""
    return AppConfig.from_env()


# --------------------------------------------------------------------------- #
# Lazy object factories
# --------------------------------------------------------------------------- #
def build_llm(config: AppConfig) -> LLM:
    """Construct a CrewAI ``LLM`` bound to the Groq provider for ``config``."""
    from crewai import LLM

    from .compat import patch_litellm_cache_breakpoint

    # Groq (routed through LiteLLM) rejects CrewAI's internal cache_breakpoint
    # marker; install the compatibility shim before any request is made.
    patch_litellm_cache_breakpoint()

    # CrewAI/LiteLLM read the key from the environment; make it available without
    # clobbering an explicitly exported value.
    os.environ.setdefault("GROQ_API_KEY", config.groq_api_key)
    return LLM(
        model=f"groq/{config.groq_model}",
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


def build_web_search_tool(config: AppConfig) -> SerperDevTool:
    """Construct the Serper-backed web-search tool for ``config``."""
    from crewai_tools import SerperDevTool

    os.environ.setdefault("SERPER_API_KEY", config.serper_api_key)
    return SerperDevTool()

"""Runtime configuration and lazy factories for the LLM and web-search tool.

Design notes
------------
* Configuration is immutable (:class:`AppConfig` is a frozen dataclass) and is
  validated at construction time, so an invalid configuration fails fast with a
  clear :class:`~research_team.exceptions.ConfigError`.
* Credentials are passed *explicitly* to the LLM and search clients. They are
  never copied into ``os.environ``, so an ``AppConfig`` built in code always
  uses the keys it was given, even if different keys are exported.
* Heavy third-party imports (CrewAI, LiteLLM) happen lazily *inside* factory
  functions. This keeps ``--help``/``--version`` and unit tests fast and lets
  this module be imported without the full agent stack installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from .exceptions import ConfigError

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids importing heavy deps
    from crewai import LLM
    from crewai.tools import BaseTool

# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #
# Default model. Groq retired its Llama 3.x chat models in 2026; openai/gpt-oss-120b
# is the strongest model it currently serves and supports tool calling. On the
# free tier each model has its own budget (verified 2026-11: 1,000 requests/day
# and 8,000 tokens/minute), so openai/gpt-oss-20b is a useful faster alternative.
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b")
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 2048
#: Output budget for the final report (the longest generation of a run).
DEFAULT_SYNTHESIS_MAX_TOKENS = 3072
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_MAX_RETRIES = 3
DEFAULT_LOG_LEVEL = "INFO"

#: LLM providers the engine knows how to talk to (all through LiteLLM).
SUPPORTED_PROVIDERS = ("groq", "gemini", "openrouter", "openai_compatible", "ollama")
#: Web-search providers, tried in this order when several keys are configured.
SUPPORTED_SEARCH_PROVIDERS = ("serper", "tavily")

_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# Guard rails so that misconfiguration is caught before an API call is ever made.
_MAX_TEMPERATURE = 2.0
_MAX_REASONABLE_TOKENS = 200_000


@dataclass(frozen=True)
class AppConfig:
    """Immutable, validated application configuration.

    Instances are typically created via :meth:`from_env`, but may also be built
    directly (useful for tests or for embedding the workflow in another system).
    The first two positional fields are kept for backward compatibility with
    1.x callers.
    """

    groq_api_key: str = ""
    serper_api_key: str = ""
    groq_model: str = DEFAULT_GROQ_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    #: Output budget for the Manager Agent's final report.
    synthesis_max_tokens: int = DEFAULT_SYNTHESIS_MAX_TOKENS
    #: Retries for a *single* failed LLM call (never the whole pipeline).
    max_retries: int = DEFAULT_MAX_RETRIES
    # Optional operational guard rails for larger / long-running deployments.
    max_rpm: int | None = None
    #: Per-agent execution timeout in seconds (CrewAI ``max_execution_time``).
    request_timeout: int | None = None
    #: Wall-clock budget for a whole run in seconds (cooperative; checked per step).
    workflow_timeout: int | None = None
    log_level: str = DEFAULT_LOG_LEVEL
    verbose: bool = False
    #: Reasoning budget for reasoning models (gpt-oss, qwen3): low | medium | high.
    #: "low" keeps runs inside free-tier token-per-minute limits.
    reasoning_effort: str = DEFAULT_REASONING_EFFORT

    # --- provider selection ------------------------------------------------
    llm_provider: str = "groq"
    #: Providers tried, in order, when the current one is rate-limited/unavailable.
    fallback_providers: tuple[str, ...] = ()
    gemini_api_key: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL
    openrouter_api_key: str = ""
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    tavily_api_key: str = ""
    search_providers: tuple[str, ...] = SUPPORTED_SEARCH_PROVIDERS

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        errors: list[str] = []
        if self.llm_provider not in SUPPORTED_PROVIDERS:
            errors.append(
                f"LLM_PROVIDER must be one of {', '.join(SUPPORTED_PROVIDERS)} "
                f"(got {self.llm_provider!r})."
            )
        else:
            missing = self.missing_credentials(self.llm_provider)
            if missing:
                errors.append(missing)
        unknown_fallbacks = [p for p in self.fallback_providers if p not in SUPPORTED_PROVIDERS]
        if unknown_fallbacks:
            errors.append(
                f"LLM_FALLBACK_PROVIDERS contains unknown providers: {unknown_fallbacks}."
            )
        if not (self.serper_api_key or self.tavily_api_key):
            errors.append("SERPER_API_KEY is required (or set TAVILY_API_KEY).")
        unknown_search = [p for p in self.search_providers if p not in SUPPORTED_SEARCH_PROVIDERS]
        if unknown_search:
            errors.append(f"SEARCH_PROVIDERS contains unknown providers: {unknown_search}.")
        if not self.groq_model.strip():
            errors.append("GROQ_MODEL must not be empty.")
        if not 0.0 <= self.temperature <= _MAX_TEMPERATURE:
            errors.append(f"GROQ_TEMPERATURE must be between 0.0 and {_MAX_TEMPERATURE}.")
        if not 1 <= self.max_tokens <= _MAX_REASONABLE_TOKENS:
            errors.append(f"GROQ_MAX_TOKENS must be between 1 and {_MAX_REASONABLE_TOKENS}.")
        if not 1 <= self.synthesis_max_tokens <= _MAX_REASONABLE_TOKENS:
            errors.append(f"SYNTHESIS_MAX_TOKENS must be between 1 and {_MAX_REASONABLE_TOKENS}.")
        if self.max_retries < 0:
            errors.append("GROQ_MAX_RETRIES must be zero or greater.")
        if self.max_rpm is not None and self.max_rpm < 1:
            errors.append("MAX_RPM must be a positive integer when set.")
        if self.request_timeout is not None and self.request_timeout < 1:
            errors.append("REQUEST_TIMEOUT must be a positive integer when set.")
        if self.workflow_timeout is not None and self.workflow_timeout < 1:
            errors.append("WORKFLOW_TIMEOUT must be a positive integer when set.")
        if self.reasoning_effort not in {"low", "medium", "high"}:
            errors.append("REASONING_EFFORT must be low, medium or high.")
        if self.log_level.strip().upper() not in _VALID_LOG_LEVELS:
            errors.append(f"LOG_LEVEL must be one of {', '.join(sorted(_VALID_LOG_LEVELS))}.")
        if errors:
            raise ConfigError(" ".join(errors))

    def missing_credentials(self, provider: str) -> str | None:
        """Return an error message if ``provider`` lacks required settings."""
        if provider == "groq" and not self.groq_api_key:
            return "GROQ_API_KEY is required."
        if provider == "gemini" and not self.gemini_api_key:
            return "GEMINI_API_KEY is required when using the gemini provider."
        if provider == "openrouter" and not self.openrouter_api_key:
            return "OPENROUTER_API_KEY is required when using the openrouter provider."
        if provider == "openai_compatible" and not (
            self.openai_compatible_base_url and self.openai_compatible_model
        ):
            return "OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_MODEL are required."
        if provider == "ollama" and not self.ollama_base_url:
            return "OLLAMA_BASE_URL is required when using the ollama provider."
        return None

    @property
    def normalized_log_level(self) -> str:
        return self.log_level.strip().upper()

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
            load_environment()

        env = os.getenv
        return cls(
            groq_api_key=env("GROQ_API_KEY", "").strip(),
            serper_api_key=env("SERPER_API_KEY", "").strip(),
            groq_model=(env("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL),
            temperature=_parse_float(
                env("GROQ_TEMPERATURE"), DEFAULT_TEMPERATURE, "GROQ_TEMPERATURE"
            ),
            max_tokens=_parse_int(env("GROQ_MAX_TOKENS"), DEFAULT_MAX_TOKENS, "GROQ_MAX_TOKENS"),
            synthesis_max_tokens=_parse_int(
                env("SYNTHESIS_MAX_TOKENS"), DEFAULT_SYNTHESIS_MAX_TOKENS, "SYNTHESIS_MAX_TOKENS"
            ),
            max_retries=_parse_int(
                env("GROQ_MAX_RETRIES"), DEFAULT_MAX_RETRIES, "GROQ_MAX_RETRIES"
            ),
            max_rpm=_parse_optional_int(env("MAX_RPM"), "MAX_RPM"),
            request_timeout=_parse_optional_int(env("REQUEST_TIMEOUT"), "REQUEST_TIMEOUT"),
            workflow_timeout=_parse_optional_int(env("WORKFLOW_TIMEOUT"), "WORKFLOW_TIMEOUT"),
            log_level=(env("LOG_LEVEL", "").strip() or DEFAULT_LOG_LEVEL),
            reasoning_effort=(
                env("REASONING_EFFORT", "").strip().lower() or DEFAULT_REASONING_EFFORT
            ),
            llm_provider=(env("LLM_PROVIDER", "").strip().lower() or "groq"),
            fallback_providers=_parse_csv(env("LLM_FALLBACK_PROVIDERS")),
            gemini_api_key=env("GEMINI_API_KEY", "").strip(),
            gemini_model=(env("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL),
            openrouter_api_key=env("OPENROUTER_API_KEY", "").strip(),
            openrouter_model=(env("OPENROUTER_MODEL", "").strip() or DEFAULT_OPENROUTER_MODEL),
            openai_compatible_base_url=env("OPENAI_COMPATIBLE_BASE_URL", "").strip(),
            openai_compatible_api_key=env("OPENAI_COMPATIBLE_API_KEY", "").strip(),
            openai_compatible_model=env("OPENAI_COMPATIBLE_MODEL", "").strip(),
            ollama_base_url=(env("OLLAMA_BASE_URL", "").strip() or DEFAULT_OLLAMA_BASE_URL),
            ollama_model=(env("OLLAMA_MODEL", "").strip() or DEFAULT_OLLAMA_MODEL),
            tavily_api_key=env("TAVILY_API_KEY", "").strip(),
            search_providers=_parse_csv(env("SEARCH_PROVIDERS")) or SUPPORTED_SEARCH_PROVIDERS,
        )


def load_environment() -> None:
    """Load a local ``.env`` file into the process environment (if present).

    Existing environment variables always win over values in ``.env``.
    """
    from dotenv import load_dotenv

    load_dotenv(override=False)


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


def _parse_csv(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip().lower() for item in (value or "").split(",") if item.strip())


# --------------------------------------------------------------------------- #
# Cached default configuration
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the process-wide default configuration built from the environment."""
    return AppConfig.from_env()


# --------------------------------------------------------------------------- #
# Lazy object factories (kept for backward compatibility with 1.x callers)
# --------------------------------------------------------------------------- #
def build_llm(config: AppConfig) -> LLM:
    """Construct a CrewAI ``LLM`` for the configured primary provider."""
    from .providers import build_llm as _build_llm
    from .providers import resolve_providers

    return _build_llm(resolve_providers(config)[0], config)


def build_web_search_tool(config: AppConfig) -> BaseTool:
    """Construct the web-search tool (Serper, falling back to Tavily) for ``config``."""
    from .search import SourceCollector, build_search_provider, build_search_tool

    provider = build_search_provider(
        serper_api_key=config.serper_api_key,
        tavily_api_key=config.tavily_api_key,
        order=config.search_providers,
    )
    return build_search_tool(provider, SourceCollector())

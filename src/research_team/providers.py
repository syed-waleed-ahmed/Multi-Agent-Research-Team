"""LLM provider abstraction, per-call retries, and cooperative cancellation.

Providers
---------
Every provider is reached through LiteLLM (``is_litellm=True``), so one code
path handles Groq (the default), Google Gemini, OpenRouter, any
OpenAI-compatible endpoint, and a self-hosted Ollama server. Credentials are
passed explicitly to each client and are never written to ``os.environ``.

Retries
-------
:class:`CallGuard` wraps each *individual* LLM request. A transient failure
(rate limit, timeout, connection error, 5xx) retries only that request, with
exponential backoff plus jitter, honouring a provider's ``Retry-After`` header
when present. The expensive multi-agent pipeline is never restarted because one
call failed. If retries are exhausted, the engine may switch to the next
configured fallback provider for the *current stage only*.

Cancellation
------------
Before every LLM call the guard checks the run's :class:`RunControl`, so a
cancelled or timed-out run stops at the next agent step.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from .config import AppConfig
from .exceptions import ConfigError, ProviderUnavailableError, RateLimitExceededError
from .logging_config import get_logger
from .progress import EventType, ProgressCallback, ProgressEvent, RunControl, Stage, emit

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewai import LLM

log = get_logger("providers")

_BASE_RETRY_DELAY = 2.0
_MAX_RETRY_DELAY = 60.0
_REASONING_MODEL_MARKERS = ("gpt-oss", "qwen3", "deepseek-r1", "o3", "o4")


@dataclass(frozen=True)
class ProviderSpec:
    """Everything needed to build an LLM client for one provider."""

    name: str
    label: str
    model: str
    litellm_model: str
    api_key: str | None = None
    base_url: str | None = None

    def __repr__(self) -> str:  # never leak credentials into logs
        return f"ProviderSpec(name={self.name!r}, model={self.model!r})"


_LABELS = {
    "groq": "Groq",
    "gemini": "Google Gemini",
    "openrouter": "OpenRouter",
    "openai_compatible": "OpenAI-compatible endpoint",
    "ollama": "Ollama (self-hosted)",
}


def provider_spec(name: str, config: AppConfig, model: str | None = None) -> ProviderSpec:
    """Build the :class:`ProviderSpec` for provider ``name``."""
    missing = config.missing_credentials(name)
    if missing:
        raise ConfigError(missing)
    label = _LABELS[name]
    if name == "groq":
        chosen = model or config.groq_model
        return ProviderSpec(name, label, chosen, f"groq/{chosen}", api_key=config.groq_api_key)
    if name == "gemini":
        chosen = model or config.gemini_model
        return ProviderSpec(name, label, chosen, f"gemini/{chosen}", api_key=config.gemini_api_key)
    if name == "openrouter":
        chosen = model or config.openrouter_model
        return ProviderSpec(
            name, label, chosen, f"openrouter/{chosen}", api_key=config.openrouter_api_key
        )
    if name == "openai_compatible":
        chosen = model or config.openai_compatible_model
        return ProviderSpec(
            name,
            label,
            chosen,
            f"openai/{chosen}",
            # Many local servers accept any key; LiteLLM requires a non-empty one.
            api_key=config.openai_compatible_api_key or "not-needed",
            base_url=config.openai_compatible_base_url,
        )
    if name == "ollama":
        chosen = model or config.ollama_model
        return ProviderSpec(
            name, label, chosen, f"ollama/{chosen}", base_url=config.ollama_base_url
        )
    raise ConfigError(f"Unknown LLM provider {name!r}.")  # pragma: no cover - validated earlier


def resolve_providers(config: AppConfig, model: str | None = None) -> list[ProviderSpec]:
    """Primary provider (optionally with a model override) followed by usable fallbacks.

    Fallbacks without credentials are skipped with a warning rather than
    failing the run: they are an optional safety net.
    """
    specs = [provider_spec(config.llm_provider, config, model)]
    seen = {(specs[0].name, specs[0].model)}
    for entry in config.fallback_providers:
        # "provider" or "provider:model" — e.g. "groq:openai/gpt-oss-20b". Free-tier
        # token-per-minute limits are per model, so another model on the same
        # provider is a genuine, free fallback.
        name, _, fallback_model = entry.partition(":")
        if config.missing_credentials(name):
            log.warning("Skipping fallback provider %s: not configured", name)
            continue
        spec = provider_spec(name, config, fallback_model or None)
        if (spec.name, spec.model) in seen:
            continue
        seen.add((spec.name, spec.model))
        specs.append(spec)
    return specs


# --------------------------------------------------------------------------- #
# Transient-error classification (defensive against LiteLLM version drift)
# --------------------------------------------------------------------------- #
def transient_error_types() -> tuple[type[BaseException], ...]:
    """LiteLLM exception classes that are safe to retry."""
    try:
        import litellm.exceptions as le
    except Exception:  # pragma: no cover - litellm always present at runtime
        return ()
    names = (
        "RateLimitError",
        "Timeout",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
    )
    return tuple(
        cls
        for name in names
        if isinstance(cls := getattr(le, name, None), type) and issubclass(cls, BaseException)
    )


def fatal_provider_error_types() -> tuple[type[BaseException], ...]:
    """LiteLLM errors that retrying cannot fix (credentials, model, permissions)."""
    try:
        import litellm.exceptions as le
    except Exception:  # pragma: no cover - litellm always present at runtime
        return ()
    names = ("AuthenticationError", "NotFoundError", "PermissionDeniedError")
    return tuple(
        cls
        for name in names
        if isinstance(cls := getattr(le, name, None), type) and issubclass(cls, BaseException)
    )


def rate_limit_error_type() -> type[BaseException] | None:
    try:
        from litellm.exceptions import RateLimitError

        return RateLimitError
    except Exception:  # pragma: no cover
        return None


_TRY_AGAIN_IN = re.compile(
    r"try again in\s+(?:(?P<m>\d+)m)?(?P<n>\d+(?:\.\d+)?)(?P<unit>ms|s)\b", re.IGNORECASE
)


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Extract the provider's wait hint (seconds) from a rate-limit error.

    Uses the ``Retry-After`` header when the response carries one, otherwise the
    provider's message (Groq: "Please try again in 7.66s" / "in 1m2.5s" /
    "in 520ms").
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        try:
            value = headers.get("retry-after")
            if value is not None:
                return max(0.0, float(value))
        except (TypeError, ValueError):
            pass
        except Exception:  # pragma: no cover - defensive
            pass
    match = _TRY_AGAIN_IN.search(str(exc))
    if match is None:
        return None
    amount = float(match.group("n"))
    seconds = amount / 1000 if match.group("unit").lower() == "ms" else amount
    return int(match.group("m") or 0) * 60 + seconds


class CallGuard:
    """Retries one LLM call with backoff + jitter and enforces cancellation.

    The guard is pure Python and fully unit-testable without CrewAI.
    """

    def __init__(
        self,
        *,
        control: RunControl | None = None,
        max_retries: int = 3,
        on_progress: ProgressCallback | None = None,
        provider: str = "",
        base_delay: float = _BASE_RETRY_DELAY,
        max_delay: float = _MAX_RETRY_DELAY,
        rng: Callable[[], float] = random.random,
        transient: tuple[type[BaseException], ...] | None = None,
        rate_limit: type[BaseException] | None = None,
        fatal: tuple[type[BaseException], ...] | None = None,
        rate_limit_budget: float = 60.0,
    ) -> None:
        self.control = control or RunControl()
        self.max_retries = max_retries
        #: Total seconds one request may spend waiting out rate limits. Free-tier
        #: token-per-minute windows need up to a minute to clear, so rate limits
        #: are retried against a time budget rather than a fixed attempt count.
        self.rate_limit_budget = rate_limit_budget
        self.on_progress = on_progress
        self.provider = provider
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._rng = rng
        self._transient = transient if transient is not None else transient_error_types()
        self._rate_limit = rate_limit if transient is not None else rate_limit_error_type()
        self._fatal = fatal if fatal is not None else fatal_provider_error_types()
        self._stage: Stage | None = None
        self.calls = 0
        #: Terminal error that "tripped" the guard for the current stage. CrewAI's
        #: executor may re-invoke the LLM after an error (e.g. falling back from
        #: native tool calling to text parsing); once tripped, those extra calls
        #: fail immediately instead of hitting an exhausted provider again.
        self._tripped: BaseException | None = None

    @property
    def stage(self) -> Stage | None:
        """The stage currently executing; set by the engine before each stage."""
        return self._stage

    @stage.setter
    def stage(self, value: Stage | None) -> None:
        self._stage = value
        self._tripped = None  # a new stage (or a fallback attempt) starts clean

    def delay_for(self, attempt: int, exc: BaseException | None = None) -> float:
        """Backoff for retry ``attempt`` (1-based): exponential, capped, jittered."""
        exponential = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        delay = exponential * (0.5 + self._rng() / 2)  # "equal jitter"
        hint = _retry_after_seconds(exc) if exc is not None else None
        if hint is not None:
            delay = max(delay, min(hint, self.max_delay))
        return delay

    def run(self, call: Callable[[], Any]) -> Any:
        if self._tripped is not None:
            raise self._tripped
        try:
            return self._run(call)
        except (RateLimitExceededError, ProviderUnavailableError) as exc:
            self._tripped = exc
            raise

    def _run(self, call: Callable[[], Any]) -> Any:
        attempt = 0
        transient_failures = 0
        rate_limit_waited = 0.0
        while True:
            self.control.check()
            self.calls += 1
            emit(
                self.on_progress,
                ProgressEvent(
                    EventType.LLM_CALL,
                    self.stage,
                    "Model request sent",
                    {"provider": self.provider, "attempt": attempt + 1},
                ),
            )
            try:
                return call()
            except self._fatal as exc:  # type: ignore[misc]
                # Not retryable: bad key, unknown model, or no access. Surface a clear
                # error; the engine may still switch to a fallback provider.
                raise ProviderUnavailableError(
                    f"{self.provider} rejected the request ({type(exc).__name__}): {exc}",
                    public_message=(
                        "The AI provider rejected the request (invalid API key or unavailable "
                        "model). The server operator needs to update its configuration."
                    ),
                ) from exc
            except self._transient as exc:  # type: ignore[misc]
                attempt += 1
                is_rate_limit = self._rate_limit is not None and isinstance(exc, self._rate_limit)
                delay = self.delay_for(attempt, exc)
                if is_rate_limit:
                    if rate_limit_waited + delay > self.rate_limit_budget:
                        raise RateLimitExceededError(
                            f"{self.provider} kept rate-limiting the request after waiting "
                            f"{rate_limit_waited:.0f}s: {exc}"
                        ) from exc
                    rate_limit_waited += delay
                else:
                    transient_failures += 1
                    if transient_failures > self.max_retries:
                        raise ProviderUnavailableError(
                            f"{self.provider} failed after {self.max_retries} retries: {exc}"
                        ) from exc
                reason = "rate limited" if is_rate_limit else type(exc).__name__
                log.warning(
                    "Transient %s error (%s); retry #%d in %.1fs",
                    self.provider,
                    reason,
                    attempt,
                    delay,
                )
                emit(
                    self.on_progress,
                    ProgressEvent(
                        EventType.RETRY,
                        self.stage,
                        f"Provider {reason}; retrying in {delay:.0f}s",
                        {
                            "provider": self.provider,
                            "attempt": attempt,
                            "max_retries": self.max_retries,
                            "delay_seconds": round(delay, 1),
                            "rate_limited": is_rate_limit,
                        },
                    ),
                )
                self.control.wait(delay)


# --------------------------------------------------------------------------- #
# CrewAI LLM subclass
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _guarded_llm_class() -> type[LLM]:
    """Create (once) an ``LLM`` subclass whose ``call`` goes through a CallGuard.

    Defined lazily so importing this module never imports CrewAI.
    """
    from crewai import LLM
    from pydantic import PrivateAttr

    class GuardedLLM(LLM):  # type: ignore[misc, valid-type]
        _guard: CallGuard | None = PrivateAttr(default=None)

        def call(self, messages: Any, *args: Any, **kwargs: Any) -> Any:
            parent_call = super().call
            guard = self._guard
            if guard is None:
                return parent_call(messages, *args, **kwargs)
            return guard.run(lambda: parent_call(messages, *args, **kwargs))

    return GuardedLLM


def build_llm(
    spec: ProviderSpec,
    config: AppConfig,
    *,
    guard: CallGuard | None = None,
    max_tokens: int | None = None,
) -> LLM:
    """Construct a CrewAI LLM for ``spec`` (always routed through LiteLLM)."""
    from .compat import patch_litellm_cache_breakpoint

    # Groq (via LiteLLM) rejects CrewAI's internal cache_breakpoint marker;
    # install the compatibility shim before any request is made.
    patch_litellm_cache_breakpoint()

    kwargs: dict[str, Any] = {
        "model": spec.litellm_model,
        "is_litellm": True,
        "temperature": config.temperature,
        "max_tokens": max_tokens or config.max_tokens,
    }
    if spec.api_key:
        kwargs["api_key"] = spec.api_key
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    if any(marker in spec.model.lower() for marker in _REASONING_MODEL_MARKERS):
        kwargs["reasoning_effort"] = config.reasoning_effort

    llm = _guarded_llm_class()(**kwargs)
    llm._guard = guard
    return llm


def token_usage(llm: Any) -> dict[str, int]:
    """Best-effort token-usage snapshot from a CrewAI LLM."""
    getter = getattr(llm, "get_token_usage_summary", None)
    if not callable(getter):
        return {}
    try:
        summary = getter()
        data = summary.model_dump() if hasattr(summary, "model_dump") else dict(summary)
    except Exception:  # pragma: no cover - defensive
        return {}
    return {k: int(v) for k, v in data.items() if isinstance(v, (int, float))}


def usage_delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {k: after.get(k, 0) - before.get(k, 0) for k in after}

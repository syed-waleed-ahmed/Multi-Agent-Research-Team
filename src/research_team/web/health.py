"""Provider health checks for the readiness endpoint.

Checks are cheap and cached: they call free metadata endpoints (model lists),
never a billable completion or search. For Groq the check also confirms the
configured model is still served — catching a retired model *before* users
hit errors (Groq retired its Llama 3.x chat models in 2026).

Web-search providers are reported as "configured" without a live probe,
because every Serper/Tavily request consumes free quota.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import httpx

from ..config import AppConfig
from ..logging_config import get_logger

log = get_logger("web.health")

_CACHE_TTL_SECONDS = 300.0
_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


class ProviderHealth:
    """Caches the result of a lightweight LLM-provider probe."""

    def __init__(self, ttl_seconds: float = _CACHE_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds
        self._cached: tuple[float, CheckResult] | None = None
        self._lock = threading.Lock()

    def check(self, config: AppConfig, model: str) -> CheckResult:
        with self._lock:
            if self._cached and time.monotonic() - self._cached[0] < self.ttl:
                return self._cached[1]
        result = self._probe(config, model)
        with self._lock:
            self._cached = (time.monotonic(), result)
        return result

    def _probe(self, config: AppConfig, model: str) -> CheckResult:
        provider = config.llm_provider
        name = f"llm:{provider}"
        try:
            if provider == "groq":
                response = httpx.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {config.groq_api_key}"},
                    timeout=_TIMEOUT_SECONDS,
                )
                if response.status_code != 200:
                    return CheckResult(name, False, f"Groq returned HTTP {response.status_code}")
                served = {item.get("id") for item in response.json().get("data", [])}
                if model not in served:
                    return CheckResult(name, False, f"Model {model!r} is not served by Groq")
                return CheckResult(name, True, f"Groq reachable; {model} available")
            if provider == "openrouter":
                response = httpx.get(
                    "https://openrouter.ai/api/v1/models", timeout=_TIMEOUT_SECONDS
                )
                ok = response.status_code == 200
                return CheckResult(name, ok, f"OpenRouter HTTP {response.status_code}")
        except httpx.HTTPError as exc:
            log.warning("Provider health probe failed: %s", exc)
            return CheckResult(name, False, f"{provider} unreachable ({type(exc).__name__})")
        return CheckResult(name, True, f"{provider} configured (not probed)")

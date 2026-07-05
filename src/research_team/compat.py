"""Compatibility shims for third-party libraries.

This module isolates narrowly-scoped, defensively-guarded workarounds for known
upstream bugs so the rest of the codebase stays clean. Every shim is:

* **guarded** — wrapped in ``try/except`` so a change in the dependency's
  internals can never crash the application (it degrades to a no-op),
* **idempotent** — safe to call repeatedly, and
* **documented** — with the reason it exists and when it can be removed.
"""

from __future__ import annotations

from .logging_config import get_logger

log = get_logger("compat")

_CACHE_BREAKPOINT_FLAG = "_crewai_cache_breakpoint_patched"


def patch_litellm_cache_breakpoint() -> bool:
    """Stop CrewAI leaking its ``cache_breakpoint`` marker to LiteLLM providers.

    CrewAI (>= 1.x) marks messages with an internal ``cache_breakpoint`` key to
    drive provider-side prompt caching. Native providers translate or strip that
    key, and ``BaseLLM._format_messages`` strips it too — but the LiteLLM code
    path (``crewai.llm.LLM._format_messages_for_provider``) forwards messages
    verbatim. Providers that validate their payload strictly (for example Groq)
    then reject the request with::

        BadRequestError: property 'cache_breakpoint' is unsupported

    This shim wraps that one method to strip the marker before the request is
    sent, exactly as the surrounding code already intends. Prompt caching (a
    performance optimization) is unaffected for providers that never saw the
    marker anyway.

    Returns ``True`` if the patch is in place (or already was), ``False`` if the
    upstream surface changed and the shim safely did nothing.

    Remove this once CrewAI strips the marker on the LiteLLM path upstream.
    """
    try:
        from crewai.llm import LLM
        from crewai.llms.cache import CACHE_BREAKPOINT_KEY
    except Exception:  # pragma: no cover - crewai always present at runtime
        return False

    if getattr(LLM, _CACHE_BREAKPOINT_FLAG, False):
        return True

    original = getattr(LLM, "_format_messages_for_provider", None)
    if not callable(original):  # upstream renamed/removed the method
        log.debug("cache_breakpoint shim skipped: method not found")
        return False

    def _stripped(self, messages):  # type: ignore[no-untyped-def]
        formatted = original(self, messages)
        cleaned = []
        for message in formatted:
            if isinstance(message, dict) and CACHE_BREAKPOINT_KEY in message:
                message = {k: v for k, v in message.items() if k != CACHE_BREAKPOINT_KEY}
            cleaned.append(message)
        return cleaned

    LLM._format_messages_for_provider = _stripped  # type: ignore[method-assign]
    setattr(LLM, _CACHE_BREAKPOINT_FLAG, True)
    log.debug("Applied CrewAI/LiteLLM cache_breakpoint compatibility shim")
    return True

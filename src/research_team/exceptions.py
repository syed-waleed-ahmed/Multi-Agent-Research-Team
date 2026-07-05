"""Typed exception hierarchy for the Multi-Agent Research Team.

Using a small, well-defined exception hierarchy lets callers (the CLI, an HTTP
layer, a job runner, tests) distinguish *why* a run failed and react with the
appropriate exit code or retry policy instead of parsing error strings.
"""

from __future__ import annotations


class ResearchTeamError(Exception):
    """Base class for all errors raised by this package."""


class ConfigError(ResearchTeamError):
    """Raised when configuration is missing or invalid.

    Typically caused by absent API keys or out-of-range tuning values.
    """


class DependencyError(ResearchTeamError):
    """Raised when a required third-party dependency is not installed."""


class WorkflowError(ResearchTeamError):
    """Raised when the research workflow fails to produce a result."""


class RateLimitExceededError(WorkflowError):
    """Raised when the upstream model provider rate-limits the request.

    This is a specialization of :class:`WorkflowError` so that callers may
    surface provider-specific guidance (for example: pick a lighter model or
    lower the token budget) or apply a backoff-and-retry policy.
    """

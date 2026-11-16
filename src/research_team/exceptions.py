"""Typed exception hierarchy for the Multi-Agent Research Team.

Using a small, well-defined exception hierarchy lets callers (the CLI, the web
API, a job runner, tests) distinguish *why* a run failed and react with the
appropriate exit code, HTTP status, or retry policy instead of parsing error
strings.

Every exception carries a ``public_message``: a short, user-safe explanation
that never includes provider payloads, stack traces, or configuration values.
The web layer shows only that message to browsers; the full exception is logged
server-side.
"""

from __future__ import annotations


class ResearchTeamError(Exception):
    """Base class for all errors raised by this package."""

    #: Safe, generic text shown to end users when the specific message may
    #: contain internal details. Subclasses override it.
    public_message = "The research workflow failed."

    def __init__(self, message: str = "", *, public_message: str | None = None) -> None:
        super().__init__(message or self.public_message)
        if public_message is not None:
            self.public_message = public_message


class ConfigError(ResearchTeamError):
    """Raised when configuration is missing or invalid.

    Typically caused by absent API keys or out-of-range tuning values.
    """

    public_message = "The server is not configured correctly."


class DependencyError(ResearchTeamError):
    """Raised when a required third-party dependency is not installed."""

    public_message = "A required server component is not installed."


class WorkflowError(ResearchTeamError):
    """Raised when the research workflow fails to produce a result."""

    public_message = "The research workflow failed. Please try again later."


class RateLimitExceededError(WorkflowError):
    """Raised when the upstream model provider rate-limits the request.

    This is a specialization of :class:`WorkflowError` so that callers may
    surface provider-specific guidance (for example: pick a lighter model or
    lower the token budget) or apply a backoff-and-retry policy.
    """

    public_message = (
        "The AI provider's free-tier rate limit was reached. Please wait a minute and try again."
    )


class ProviderUnavailableError(WorkflowError):
    """Raised when every configured provider failed with a non-rate-limit error."""

    public_message = "The AI provider is temporarily unavailable. Please try again later."


class WorkflowCancelledError(WorkflowError):
    """Raised when a run is cancelled cooperatively before it finishes."""

    public_message = "The research run was cancelled."


class WorkflowTimeoutError(WorkflowError):
    """Raised when a run exceeds its configured wall-clock budget."""

    public_message = "The research run exceeded its time limit."

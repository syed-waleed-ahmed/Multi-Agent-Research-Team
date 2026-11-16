"""Multi-Agent Research Team.

An open-source research engine that coordinates a team of specialized CrewAI
agents (research, coding/analysis, and a synthesizing manager) to research a
topic and produce a professional Markdown report. It ships with a CLI and a web
application (``research_team.web``).

The public surface of the package is intentionally small so that the workflow
can be embedded in larger systems (for example a web API or a background job
runner) without depending on CLI internals.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "__version__",
    "AppConfig",
    "ResearchOptions",
    "ResearchResult",
    "RunControl",
    "ProgressEvent",
    "run_research_workflow",
    "ResearchTeamError",
    "ConfigError",
    "DependencyError",
    "WorkflowError",
    "RateLimitExceededError",
    "ProviderUnavailableError",
    "WorkflowCancelledError",
    "WorkflowTimeoutError",
]

#: The single source of truth for the package version (read by pyproject.toml).
__version__ = "2.0.1"


_EXCEPTION_NAMES = frozenset(
    {
        "ResearchTeamError",
        "ConfigError",
        "DependencyError",
        "WorkflowError",
        "RateLimitExceededError",
        "ProviderUnavailableError",
        "WorkflowCancelledError",
        "WorkflowTimeoutError",
    }
)


def __getattr__(name: str) -> Any:
    """Lazily expose the public API without importing heavy dependencies eagerly.

    Importing :mod:`research_team` should be cheap (for example to read
    :data:`__version__`). Heavy objects that pull in CrewAI/LiteLLM are only
    resolved when they are actually accessed.
    """
    if name == "AppConfig":
        from .config import AppConfig

        return AppConfig
    if name in {"ResearchResult", "ResearchOptions", "run_research_workflow"}:
        from . import crew

        return getattr(crew, name)
    if name in {"RunControl", "ProgressEvent"}:
        from . import progress

        return getattr(progress, name)
    if name in _EXCEPTION_NAMES:
        from . import exceptions

        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Progress reporting and cooperative cancellation for a research run.

The research engine emits :class:`ProgressEvent` objects to an optional
observer callback as it *actually* executes. Nothing here is simulated: every
event corresponds to a real state transition inside the engine (a stage
starting, a search query being sent, a retry being scheduled, ...). The web
layer persists these events and streams them to the browser; the CLI logs them.

:class:`RunControl` carries the cancellation flag and wall-clock deadline for a
run. The engine checks it at every safe interruption point (before each stage,
before each LLM call, before each search request, and while waiting between
retries), so cancellation and timeouts take effect at the next agent step
instead of only after the whole pipeline finishes.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .exceptions import WorkflowCancelledError, WorkflowTimeoutError


class Stage(str, Enum):
    """The three sequential stages of the research pipeline."""

    RESEARCH = "research"
    CODING = "coding"
    SYNTHESIS = "synthesis"

    @property
    def agent_name(self) -> str:
        return _AGENT_NAMES[self]


_AGENT_NAMES = {
    Stage.RESEARCH: "Research Agent",
    Stage.CODING: "Coding Agent",
    Stage.SYNTHESIS: "Manager Agent",
}

#: Execution order of the pipeline.
STAGES: tuple[Stage, ...] = (Stage.RESEARCH, Stage.CODING, Stage.SYNTHESIS)


class EventType(str, Enum):
    """Kinds of progress events emitted by the engine."""

    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    LLM_CALL = "llm_call"
    SEARCH = "search"
    RETRY = "retry"
    PROVIDER_FALLBACK = "provider_fallback"
    RUN_COMPLETED = "run_completed"


@dataclass(frozen=True)
class ProgressEvent:
    """A single, real state transition inside the engine."""

    type: EventType
    stage: Stage | None = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


#: Signature of an observer that receives progress events.
ProgressCallback = Callable[[ProgressEvent], None]


class RunControl:
    """Thread-safe cancellation flag plus an optional wall-clock deadline."""

    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._cancelled = threading.Event()
        self._deadline = time.monotonic() + timeout_seconds if timeout_seconds else None
        self.timeout_seconds = timeout_seconds

    def cancel(self) -> None:
        """Request cancellation; the engine stops at its next checkpoint."""
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def remaining(self) -> float | None:
        """Seconds left before the deadline, or ``None`` when unbounded."""
        if self._deadline is None:
            return None
        return max(0.0, self._deadline - time.monotonic())

    def check(self) -> None:
        """Raise if the run was cancelled or its deadline has passed."""
        if self._cancelled.is_set():
            raise WorkflowCancelledError("Run cancelled by request.")
        if self._deadline is not None and time.monotonic() >= self._deadline:
            raise WorkflowTimeoutError(
                f"Run exceeded its {self.timeout_seconds:.0f}s time limit.",
                public_message=(
                    f"The research run exceeded its {self.timeout_seconds:.0f}-second time limit."
                ),
            )

    def wait(self, seconds: float) -> None:
        """Sleep for ``seconds`` but wake immediately on cancellation.

        Raises if the run is cancelled during the wait or if the wait would
        outlive the deadline.
        """
        remaining = self.remaining()
        if remaining is not None and seconds >= remaining:
            # Waiting would blow the budget; fail fast with a timeout.
            self._cancelled.wait(remaining)
            self.check()
            raise WorkflowTimeoutError(
                f"Run exceeded its {self.timeout_seconds:.0f}s time limit while backing off."
            )
        if self._cancelled.wait(seconds):
            self.check()
        self.check()


def emit(callback: ProgressCallback | None, event: ProgressEvent) -> None:
    """Deliver ``event`` to ``callback`` without letting observer bugs break a run."""
    if callback is None:
        return
    try:
        callback(event)
    except Exception:  # pragma: no cover - defensive: observers must never crash the engine
        from .logging_config import get_logger

        get_logger("progress").exception("Progress observer raised; continuing run")

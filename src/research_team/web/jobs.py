"""Background job execution for research runs.

Execution model
---------------
* Jobs are **persisted first** (status ``queued``) and then handed to a bounded
  :class:`~concurrent.futures.ThreadPoolExecutor`. CrewAI is synchronous, so
  runs execute in worker threads and never block the API's event loop.
* ``MAX_CONCURRENT_JOBS`` caps parallel runs (default 1: free-tier LLM quotas
  are per account, so parallel runs mostly just collide on rate limits).
  ``MAX_QUEUED_JOBS`` caps the backlog; the API rejects work beyond it.
* **Heartbeats and recovery.** A worker refreshes ``heartbeat_at`` on its
  running jobs every 15 s. At startup and every 30 s, jobs whose heartbeat is
  stale (> 90 s) are marked ``failed`` with code ``interrupted`` (partial work
  cannot be resumed) and unclaimed ``queued`` jobs are picked up. Jobs that
  another live instance is still executing (e.g. during a zero-downtime
  deploy) are left alone.
* **Graceful shutdown.** On SIGTERM no new job starts; running jobs get up to
  ``SHUTDOWN_DRAIN_SECONDS`` to finish before they are stopped, and queued
  jobs stay queued for the next instance.
* **Cancellation** is cooperative: a queued job is cancelled immediately; a
  running job stops at the engine's next checkpoint (before its next model
  request or search).
* A janitor thread deletes expired jobs so storage stays bounded.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from ..config import AppConfig
from ..crew import ResearchOptions, ResearchResult, run_research_workflow
from ..exceptions import (
    ConfigError,
    ProviderUnavailableError,
    RateLimitExceededError,
    ResearchTeamError,
    WorkflowCancelledError,
    WorkflowTimeoutError,
)
from ..logging_config import get_logger
from ..progress import EventType, ProgressEvent, RunControl
from . import repository as repo
from .db import Database
from .schemas import JobStatus, StageStatus
from .settings import WebSettings

log = get_logger("web.jobs")

#: Signature of the function that performs a run (injectable for tests).
Runner = Callable[..., ResearchResult]

_CLEANUP_INTERVAL_SECONDS = 600
#: How often a worker records that it is still executing its jobs.
_HEARTBEAT_SECONDS = 15
#: A running job whose heartbeat is older than this is treated as orphaned.
_STALE_AFTER_SECONDS = 90
#: How often to look for orphaned running jobs and unclaimed queued jobs.
_SWEEP_SECONDS = 30


class JobObserver:
    """Persists engine events and mirrors them into per-stage progress."""

    def __init__(self, db: Database, job_id: str) -> None:
        self.db = db
        self.job_id = job_id

    def __call__(self, event: ProgressEvent) -> None:
        stage = event.stage.value if event.stage else None
        with self.db.session() as session:
            repo.add_event(
                session, self.job_id, event.type.value, stage, event.message, _jsonable(event.data)
            )
            if stage is None:
                return
            now = repo.utcnow().isoformat()
            if event.type is EventType.STAGE_STARTED:
                repo.update_stage(
                    session,
                    self.job_id,
                    stage,
                    status=StageStatus.RUNNING.value,
                    started_at=now,
                    finished_at=None,
                    **{"+attempts": 1},
                )
            elif event.type is EventType.STAGE_COMPLETED:
                repo.update_stage(
                    session, self.job_id, stage, status=StageStatus.COMPLETED.value, finished_at=now
                )
            elif event.type is EventType.STAGE_FAILED:
                cancelled = event.data.get("error_type") == "WorkflowCancelledError"
                status = StageStatus.CANCELLED if cancelled else StageStatus.FAILED
                repo.update_stage(session, self.job_id, stage, status=status.value, finished_at=now)
            elif event.type is EventType.SEARCH:
                repo.update_stage(session, self.job_id, stage, **{"+searches": 1})
            elif event.type is EventType.LLM_CALL:
                repo.update_stage(session, self.job_id, stage, **{"+llm_calls": 1})


def _jsonable(data: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v for k, v in data.items() if isinstance(v, (str, int, float, bool, list, type(None)))
    }


def result_payload(result: ResearchResult) -> dict[str, Any]:
    """Serialise a :class:`ResearchResult` for storage (matches ``ResultOut``)."""
    return {
        "report_markdown": result.report,
        "document_markdown": result.document or result.report,
        "research_notes": result.research_notes,
        "code_examples": result.code_examples,
        "methodology_markdown": result.methodology,
        "sources": [asdict(source) for source in result.sources],
        "citation_check": result.citation_check.to_dict(),
        "search_queries": list(result.search_queries),
        "model": result.model,
        "provider": result.provider,
        "duration_seconds": round(result.duration_seconds, 2),
        "token_usage": dict(result.token_usage),
        "truncated": result.truncated,
    }


def _error_for(exc: BaseException) -> tuple[JobStatus, str, str]:
    """Map an exception to (status, error_code, user-safe message)."""
    if isinstance(exc, WorkflowCancelledError):
        return JobStatus.CANCELLED, "cancelled", exc.public_message
    if isinstance(exc, WorkflowTimeoutError):
        return JobStatus.FAILED, "timeout", exc.public_message
    if isinstance(exc, RateLimitExceededError):
        return JobStatus.FAILED, "rate_limited", exc.public_message
    if isinstance(exc, ProviderUnavailableError):
        return JobStatus.FAILED, "provider_unavailable", exc.public_message
    if isinstance(exc, ConfigError):
        return JobStatus.FAILED, "configuration", exc.public_message
    if isinstance(exc, ResearchTeamError):
        return JobStatus.FAILED, "workflow_error", exc.public_message
    if isinstance(exc, ValueError):
        return JobStatus.FAILED, "invalid_request", "The request could not be processed."
    return JobStatus.FAILED, "internal_error", "An unexpected server error occurred."


class JobManager:
    """Owns the worker pool, cancellation handles, heartbeats and the janitor."""

    def __init__(
        self,
        db: Database,
        settings: WebSettings,
        config_factory: Callable[[], AppConfig],
        *,
        runner: Runner = run_research_workflow,
    ) -> None:
        self.db = db
        self.settings = settings
        self._config_factory = config_factory
        self._runner = runner
        self._executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_jobs, thread_name_prefix="research-job"
        )
        self._controls: dict[str, RunControl] = {}
        #: Job ids handed to the executor and not finished yet (prevents duplicates).
        self._submitted: set[str] = set()
        self._lock = threading.Lock()
        #: Serialises quota checks + inserts so concurrent requests cannot overshoot limits.
        self.create_lock = threading.Lock()
        #: Set when shutdown begins: no new job starts on this instance.
        self._stopping = threading.Event()
        #: Set when shutdown has finished: background threads exit.
        self._stopped = threading.Event()
        self._threads: list[threading.Thread] = []
        self.started = False

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        resumed = self.sweep()
        if resumed:
            log.info("Re-queued %d job(s) after restart", resumed)
        loops = ((self._janitor_loop, "job-janitor"), (self._heartbeat_loop, "job-heartbeat"))
        for target, name in loops:
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)
        self.started = True

    def shutdown(self, drain_seconds: float = 0.0, join_timeout: float = 15.0) -> None:
        """Graceful stop for deploys and restarts.

        1. Stop starting new jobs (queued ones stay queued for the next instance).
        2. Let running jobs finish for up to ``drain_seconds``; their heartbeat
           keeps other instances from treating them as orphaned meanwhile.
        3. Cancel whatever is still running (recorded as ``interrupted``).
        """
        self._stopping.set()
        deadline = time.monotonic() + max(0.0, drain_seconds)
        with self._lock:
            running = len(self._controls)
        if running and drain_seconds > 0:
            log.info("Draining %d running job(s) for up to %.0fs", running, drain_seconds)
        while time.monotonic() < deadline:
            with self._lock:
                if not self._controls:
                    break
            time.sleep(0.25)
        with self._lock:
            controls = list(self._controls.values())
        for control in controls:
            control.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        workers = [
            t for t in threading.enumerate() if t.name.startswith("research-job") and t.is_alive()
        ]
        for thread in workers:
            thread.join(timeout=join_timeout / max(1, len(workers)))
        self._stopped.set()
        self.started = False

    @property
    def healthy(self) -> bool:
        return self.started and not self._stopping.is_set()

    # -- operations --------------------------------------------------------
    def submit(self, job_id: str) -> None:
        if self._stopping.is_set():
            return
        with self._lock:
            if job_id in self._submitted:
                return
            self._submitted.add(job_id)
        self._executor.submit(self._execute, job_id)

    def cancel(self, job_id: str) -> str:
        """Request cancellation; returns the resulting status string."""
        with self.db.session() as session:
            if repo.cancel_if_queued(session, job_id):
                repo.add_event(
                    session, job_id, "run_cancelled", None, "Cancelled before it started", {}
                )
                return JobStatus.CANCELLED.value
            job = repo.get_job(session, job_id)
            status = job.status if job else JobStatus.FAILED.value
        with self._lock:
            control = self._controls.get(job_id)
        if control is not None:
            control.cancel()
        return status

    def sweep(self, stale_after_seconds: float = _STALE_AFTER_SECONDS) -> int:
        """Fail orphaned running jobs and pick up queued jobs; returns jobs submitted.

        Runs at startup and periodically, so work left behind by another
        instance (a crash, or a deploy that ended before a queued job started)
        is never stranded. A job whose worker is still heartbeating elsewhere is
        not touched.
        """
        stale_before = repo.utcnow() - timedelta(seconds=stale_after_seconds)
        try:
            with self.db.session() as session:
                queued = repo.recover_interrupted(session, stale_before)
        except Exception:  # pragma: no cover - janitor must never die
            log.exception("Job sweep failed")
            return 0
        with self._lock:
            new = [job_id for job_id in queued if job_id not in self._submitted]
        for job_id in new:
            self.submit(job_id)
        return len(new)

    # -- worker ------------------------------------------------------------
    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._submitted.discard(job_id)
            self._controls.pop(job_id, None)

    def _execute(self, job_id: str) -> None:
        if self._stopping.is_set():
            self._forget(job_id)  # leave it queued for the next instance
            return
        with self.db.session() as session:
            if not repo.mark_running(session, job_id):
                self._forget(job_id)
                return  # cancelled, or already taken by another instance
            job = repo.get_job(session, job_id)
            assert job is not None
            topic = job.topic
            options = ResearchOptions(
                depth=job.depth,
                report_style=job.report_style,
                instructions=job.instructions,
                model=job.model,
            )

        control = RunControl(self.settings.job_timeout_seconds)
        with self._lock:
            self._controls[job_id] = control
        observer = JobObserver(self.db, job_id)
        try:
            config = self._config_factory()
            result = self._runner(
                topic,
                config,
                options,
                on_progress=observer,
                control=control,
                max_report_chars=self.settings.max_report_chars,
            )
            with self.db.session() as session:
                repo.save_result(session, job_id, result_payload(result))
                repo.finish_job(session, job_id, JobStatus.SUCCEEDED)
            log.info("Job %s succeeded in %.1fs", job_id, result.duration_seconds)
        except BaseException as exc:  # noqa: BLE001 - every failure must be recorded
            status, code, message = _error_for(exc)
            if code == "cancelled" and self._stopping.is_set():
                # Stopped by a server shutdown, not by the user.
                status, code = JobStatus.FAILED, "interrupted"
                message = "The server restarted while this job was running. Please retry."
            if code in {"internal_error", "workflow_error", "invalid_request"}:
                log.exception("Job %s failed (%s)", job_id, code)
            else:
                log.warning("Job %s ended: %s (%s)", job_id, code, exc)
            with self.db.session() as session:
                repo.add_event(session, job_id, "run_failed", None, message, {"code": code})
                repo.finish_job(session, job_id, status, error_code=code, error_message=message)
            if not isinstance(exc, Exception):
                raise
        finally:
            self._forget(job_id)

    # -- background threads ------------------------------------------------
    def _heartbeat_loop(self) -> None:
        while not self._stopped.wait(_HEARTBEAT_SECONDS):
            with self._lock:
                running = list(self._controls)
            if not running:
                continue
            try:
                with self.db.session() as session:
                    repo.touch_heartbeats(session, running)
            except Exception:  # pragma: no cover - a missed beat is tolerated
                log.warning("Heartbeat update failed", exc_info=True)

    def _janitor_loop(self) -> None:
        last_cleanup = time.monotonic()
        while not self._stopping.wait(_SWEEP_SECONDS):
            self.sweep()
            if time.monotonic() - last_cleanup >= _CLEANUP_INTERVAL_SECONDS:
                self.cleanup()
                last_cleanup = time.monotonic()

    def cleanup(self) -> int:
        try:
            with self.db.session() as session:
                removed = repo.delete_expired(session)
            if removed:
                log.info("Deleted %d expired job(s)", removed)
            return removed
        except Exception:  # pragma: no cover - janitor must never die
            log.exception("Cleanup failed")
            return 0

    def expires_at(self) -> Any:
        return repo.utcnow() + timedelta(days=self.settings.job_retention_days)

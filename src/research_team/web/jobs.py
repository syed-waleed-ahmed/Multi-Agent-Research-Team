"""Background job execution for research runs.

Execution model
---------------
* Jobs are **persisted first** (status ``queued``) and then handed to a bounded
  :class:`~concurrent.futures.ThreadPoolExecutor`. CrewAI is synchronous, so
  runs execute in worker threads and never block the API's event loop.
* ``MAX_CONCURRENT_JOBS`` caps parallel runs (default 1: free-tier LLM quotas
  are per account, so parallel runs mostly just collide on rate limits).
  ``MAX_QUEUED_JOBS`` caps the backlog; the API rejects work beyond it.
* **Restart recovery.** On startup, jobs left ``running`` by a crashed or
  restarted process are marked ``failed`` with code ``interrupted`` (their
  partial work cannot be resumed), and ``queued`` jobs are re-submitted, so
  accepted work is not silently dropped.
* **Cancellation** is cooperative: a queued job is cancelled immediately; a
  running job stops at the engine's next checkpoint (before its next model
  request or search).
* A janitor thread deletes expired jobs so storage stays bounded.
"""

from __future__ import annotations

import threading
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
    """Owns the worker pool, cancellation handles, and the cleanup janitor."""

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
        self._lock = threading.Lock()
        #: Serialises quota checks + inserts so concurrent requests cannot overshoot limits.
        self.create_lock = threading.Lock()
        self._stopping = threading.Event()
        self._janitor: threading.Thread | None = None
        self.started = False

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        with self.db.session() as session:
            queued = repo.recover_interrupted(session)
        for job_id in queued:
            self.submit(job_id)
        if queued:
            log.info("Re-queued %d job(s) after restart", len(queued))
        self._janitor = threading.Thread(target=self._janitor_loop, name="job-janitor", daemon=True)
        self._janitor.start()
        self.started = True

    def shutdown(self, timeout: float = 20.0) -> None:
        """Graceful stop: cancel running jobs and wait briefly for workers."""
        self._stopping.set()
        with self._lock:
            controls = list(self._controls.values())
        for control in controls:
            control.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        worker_threads = [
            t for t in threading.enumerate() if t.name.startswith("research-job") and t.is_alive()
        ]
        for thread in worker_threads:
            thread.join(timeout=timeout / max(1, len(worker_threads)))
        self.started = False

    @property
    def healthy(self) -> bool:
        return self.started and not self._stopping.is_set()

    # -- operations --------------------------------------------------------
    def submit(self, job_id: str) -> None:
        if self._stopping.is_set():
            return
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

    # -- worker ------------------------------------------------------------
    def _execute(self, job_id: str) -> None:
        with self.db.session() as session:
            if not repo.mark_running(session, job_id):
                return  # cancelled (or otherwise moved on) before a worker picked it up
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
            if self._stopping.is_set():
                control.cancel()
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
            with self._lock:
                self._controls.pop(job_id, None)

    def _janitor_loop(self) -> None:
        while not self._stopping.wait(_CLEANUP_INTERVAL_SECONDS):
            self.cleanup()

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

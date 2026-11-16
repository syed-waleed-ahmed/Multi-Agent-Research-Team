"""Data-access functions for research jobs, results, and events.

All functions take an open :class:`~sqlalchemy.orm.Session`; transaction scope
is owned by the caller (see :meth:`Database.session`). State transitions use
conditional ``UPDATE ... WHERE status = ...`` statements so concurrent workers
and API requests can never move a job backwards (e.g. resurrect a cancelled job).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ..progress import STAGES
from .models import JobEvent, ResearchJob, ResearchResultRow
from .schemas import JobStatus, StageStatus

ACTIVE_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; everything is stored in UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def utc(value: datetime) -> datetime:
    """Like :func:`as_utc` for columns that are never NULL."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def new_stages() -> list[dict[str, Any]]:
    return [
        {
            "stage": stage.value,
            "agent": stage.agent_name,
            "status": StageStatus.PENDING.value,
            "started_at": None,
            "finished_at": None,
            "attempts": 0,
            "searches": 0,
            "llm_calls": 0,
        }
        for stage in STAGES
    ]


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
def create_job(session: Session, **fields: Any) -> ResearchJob:
    job = ResearchJob(
        status=JobStatus.QUEUED.value,
        stages=new_stages(),
        created_at=utcnow(),
        **fields,
    )
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: str) -> ResearchJob | None:
    return session.get(ResearchJob, job_id)


def find_idempotent(
    session: Session, client_hash: str, key: str, since: datetime
) -> ResearchJob | None:
    return session.scalars(
        select(ResearchJob)
        .where(
            ResearchJob.client_hash == client_hash,
            ResearchJob.idempotency_key == key,
            ResearchJob.created_at >= since,
        )
        .order_by(ResearchJob.created_at.desc())
        .limit(1)
    ).first()


def find_active_duplicate(session: Session, client_hash: str, cache_key: str) -> ResearchJob | None:
    return session.scalars(
        select(ResearchJob)
        .where(
            ResearchJob.client_hash == client_hash,
            ResearchJob.cache_key == cache_key,
            ResearchJob.status.in_(ACTIVE_STATUSES),
        )
        .limit(1)
    ).first()


def find_cached(session: Session, cache_key: str, since: datetime) -> ResearchJob | None:
    """Most recent succeeded job with the same normalised request."""
    return session.scalars(
        select(ResearchJob)
        .join(ResearchResultRow, ResearchResultRow.job_id == ResearchJob.id)
        .where(
            ResearchJob.cache_key == cache_key,
            ResearchJob.status == JobStatus.SUCCEEDED.value,
            ResearchJob.created_at >= since,
        )
        .order_by(ResearchJob.created_at.desc())
        .limit(1)
    ).first()


def count_created(session: Session, since: datetime, client_hash: str | None = None) -> int:
    query = select(func.count()).select_from(ResearchJob).where(ResearchJob.created_at >= since)
    if client_hash is not None:
        query = query.where(ResearchJob.client_hash == client_hash)
    return int(session.scalar(query) or 0)


def count_status(session: Session, statuses: Iterable[str]) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ResearchJob)
            .where(ResearchJob.status.in_(list(statuses)))
        )
        or 0
    )


def queue_position(session: Session, job: ResearchJob) -> int | None:
    if job.status != JobStatus.QUEUED.value:
        return None
    ahead = session.scalar(
        select(func.count())
        .select_from(ResearchJob)
        .where(
            ResearchJob.status == JobStatus.QUEUED.value,
            ResearchJob.created_at < job.created_at,
        )
    )
    return int(ahead or 0) + 1


def mark_running(session: Session, job_id: str) -> bool:
    """Atomically move ``queued`` -> ``running``. False if it was cancelled meanwhile."""
    result = session.execute(
        update(ResearchJob)
        .where(ResearchJob.id == job_id, ResearchJob.status == JobStatus.QUEUED.value)
        .values(status=JobStatus.RUNNING.value, started_at=utcnow())
    )
    return bool(getattr(result, "rowcount", 0))


def cancel_if_queued(session: Session, job_id: str) -> bool:
    result = session.execute(
        update(ResearchJob)
        .where(ResearchJob.id == job_id, ResearchJob.status == JobStatus.QUEUED.value)
        .values(
            status=JobStatus.CANCELLED.value,
            finished_at=utcnow(),
            error_code="cancelled",
            error_message="Cancelled before it started.",
        )
    )
    return bool(getattr(result, "rowcount", 0))


def finish_job(
    session: Session,
    job_id: str,
    status: JobStatus,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    job = session.get(ResearchJob, job_id)
    if job is None or job.status != JobStatus.RUNNING.value:
        return
    job.status = status.value
    job.finished_at = utcnow()
    job.error_code = error_code
    job.error_message = (error_message or "")[:1000] or None
    if status is not JobStatus.SUCCEEDED:
        terminal = (
            StageStatus.CANCELLED.value
            if status is JobStatus.CANCELLED
            else StageStatus.FAILED.value
        )
        job.stages = [
            {**s, "status": terminal, "finished_at": s["finished_at"] or utcnow().isoformat()}
            if s["status"] == StageStatus.RUNNING.value
            else s
            for s in job.stages
        ]


def update_stage(session: Session, job_id: str, stage: str, **changes: Any) -> None:
    """Merge ``changes`` into one stage entry (increments via ``+name`` keys)."""
    job = session.get(ResearchJob, job_id)
    if job is None:
        return
    stages: list[dict[str, Any]] = []
    for entry in job.stages:
        if entry["stage"] == stage:
            entry = dict(entry)
            for key, value in changes.items():
                if key.startswith("+"):
                    name = key[1:]
                    entry[name] = int(entry.get(name, 0)) + int(value)
                elif key == "started_at" and entry.get("started_at"):
                    continue  # keep the first start time across fallback attempts
                else:
                    entry[key] = value
        stages.append(entry)
    job.stages = stages  # reassign so SQLAlchemy detects the JSON change


def recover_interrupted(session: Session) -> list[str]:
    """After a restart: fail jobs that were running, return queued job ids in order.

    Stages that were running are marked failed too, so the UI never shows a
    stage "running" on a job that has already ended.
    """
    now = utcnow()
    for job in session.scalars(
        select(ResearchJob).where(ResearchJob.status == JobStatus.RUNNING.value)
    ):
        job.status = JobStatus.FAILED.value
        job.finished_at = now
        job.error_code = "interrupted"
        job.error_message = "The server restarted while this job was running. Please retry."
        job.stages = [
            {**s, "status": StageStatus.FAILED.value, "finished_at": now.isoformat()}
            if s["status"] == StageStatus.RUNNING.value
            else s
            for s in job.stages
        ]
    session.flush()
    return list(
        session.scalars(
            select(ResearchJob.id)
            .where(ResearchJob.status == JobStatus.QUEUED.value)
            .order_by(ResearchJob.created_at)
        )
    )


def delete_expired(session: Session, now: datetime | None = None) -> int:
    """Delete expired, finished jobs (results/events cascade). Returns the count."""
    now = now or utcnow()
    expired_ids = list(
        session.scalars(
            select(ResearchJob.id).where(
                ResearchJob.expires_at < now, ResearchJob.status.notin_(ACTIVE_STATUSES)
            )
        )
    )
    if not expired_ids:
        return 0
    # Explicit child deletes keep this correct even where FK cascades are off.
    session.execute(delete(JobEvent).where(JobEvent.job_id.in_(expired_ids)))
    session.execute(delete(ResearchResultRow).where(ResearchResultRow.job_id.in_(expired_ids)))
    session.execute(delete(ResearchJob).where(ResearchJob.id.in_(expired_ids)))
    return len(expired_ids)


# --------------------------------------------------------------------------- #
# Events and results
# --------------------------------------------------------------------------- #
def add_event(
    session: Session,
    job_id: str,
    type_: str,
    stage: str | None,
    message: str,
    data: dict[str, Any] | None = None,
) -> int:
    event = JobEvent(
        job_id=job_id,
        type=type_,
        stage=stage,
        message=message[:1000],
        data=data or {},
        created_at=utcnow(),
    )
    session.add(event)
    session.flush()
    return int(event.id)


def list_events(
    session: Session, job_id: str, after_id: int = 0, limit: int = 200
) -> Sequence[JobEvent]:
    return session.scalars(
        select(JobEvent)
        .where(JobEvent.job_id == job_id, JobEvent.id > after_id)
        .order_by(JobEvent.id)
        .limit(limit)
    ).all()


def save_result(session: Session, job_id: str, payload: dict[str, Any]) -> None:
    session.merge(ResearchResultRow(job_id=job_id, payload=payload, created_at=utcnow()))


def get_result(session: Session, job_id: str) -> ResearchResultRow | None:
    return session.get(ResearchResultRow, job_id)

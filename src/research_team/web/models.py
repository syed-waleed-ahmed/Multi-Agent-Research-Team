"""SQLAlchemy ORM models.

Three tables:

* ``research_jobs`` — one row per submitted research request, including its
  lifecycle status and per-stage progress (small, polled frequently).
* ``research_results`` — the (large) final output of a succeeded job, kept in a
  separate table so status polling never loads report bodies.
* ``job_events`` — an append-only log of real engine events, streamed to the
  browser over Server-Sent Events.

Schema changes go through Alembic migrations in ``migrations/versions``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    topic: Mapped[str] = mapped_column(String(1000))
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[str] = mapped_column(String(16))
    report_style: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(200))

    #: SHA-256 of the normalised request, used for result caching / dedup.
    cache_key: Mapped[str] = mapped_column(String(64), index=True)
    #: SHA-256 of the owner token (the token itself is never stored).
    owner_token_hash: Mapped[str] = mapped_column(String(64))
    #: Salted SHA-256 of the client IP (the IP itself is never stored).
    client_hash: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    #: Per-stage progress: list of {stage, agent, status, started_at, ...}.
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Refreshed periodically by the worker executing the job (liveness signal).
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("ix_research_jobs_client_created", "client_hash", "created_at"),
        Index("ix_research_jobs_created", "created_at"),
    )


class ResearchResultRow(Base):
    __tablename__ = "research_results"

    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("research_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(32))
    stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    message: Mapped[str] = mapped_column(String(1000))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

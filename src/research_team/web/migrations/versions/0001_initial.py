"""Initial schema: research jobs, results, and events.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("topic", sa.String(1000), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("depth", sa.String(16), nullable=False),
        sa.Column("report_style", sa.String(32), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("owner_token_hash", sa.String(64), nullable=False),
        sa.Column("client_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"])
    op.create_index("ix_research_jobs_cache_key", "research_jobs", ["cache_key"])
    op.create_index("ix_research_jobs_expires_at", "research_jobs", ["expires_at"])
    op.create_index("ix_research_jobs_created", "research_jobs", ["created_at"])
    op.create_index(
        "ix_research_jobs_client_created", "research_jobs", ["client_hash", "created_at"]
    )

    op.create_table(
        "research_results",
        sa.Column(
            "job_id",
            sa.String(32),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.String(32),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(16), nullable=True),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_table("job_events")
    op.drop_table("research_results")
    for index in (
        "ix_research_jobs_client_created",
        "ix_research_jobs_created",
        "ix_research_jobs_expires_at",
        "ix_research_jobs_cache_key",
        "ix_research_jobs_status",
    ):
        op.drop_index(index, table_name="research_jobs")
    op.drop_table("research_jobs")

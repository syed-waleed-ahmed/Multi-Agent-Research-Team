"""Add a worker heartbeat to research jobs.

Lets a new instance tell a crashed run (stale heartbeat) apart from one that
another instance is still executing, e.g. during a zero-downtime deploy.

Revision ID: 0002_job_heartbeat
Revises: 0001_initial
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_job_heartbeat"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    with op.batch_alter_table("research_jobs") as batch:
        batch.drop_column("heartbeat_at")

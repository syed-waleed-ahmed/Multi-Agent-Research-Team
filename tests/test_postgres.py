"""PostgreSQL integration tests (migrations, repository, full API lifecycle).

Skipped unless ``TEST_DATABASE_URL`` points at a disposable PostgreSQL
database, e.g. ``postgresql://postgres:postgres@localhost:5432/research_test``.
CI runs them against a Postgres service container; they exercise the same
``pg8000`` driver path used with Neon in production.
"""

from __future__ import annotations

import os
import secrets
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from research_team.web import repository as repo
from research_team.web.db import Database
from tests.web_helpers import FakeRunner, make_app, wait_for_status

DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith(("postgres://", "postgresql")),
    reason="TEST_DATABASE_URL (PostgreSQL) not set",
)


def test_migrations_and_repository_on_postgres():
    db = Database(DATABASE_URL)
    assert db.dialect == "postgresql"
    assert db.persistence == "persistent"
    db.migrate()
    db.migrate()  # idempotent
    job_id = secrets.token_hex(16)
    with db.session() as session:
        repo.create_job(
            session,
            id=job_id,
            topic="postgres topic",
            instructions=None,
            depth="quick",
            report_style="technical_report",
            model="openai/gpt-oss-120b",
            cache_key=job_id,
            owner_token_hash="h",
            client_hash="pg-client",
            idempotency_key=None,
            expires_at=repo.utcnow() - timedelta(days=1),
        )
        repo.add_event(session, job_id, "queued", None, "queued", {"n": 1})
    with db.session() as session:
        assert repo.mark_running(session, job_id)
        repo.update_stage(session, job_id, "research", status="running", **{"+searches": 2})
    with db.session() as session:
        job = repo.get_job(session, job_id)
        assert job.stages[0]["searches"] == 2
        assert job.created_at.tzinfo is not None
        repo.finish_job(session, job_id, repo.JobStatus.FAILED, error_code="timeout")
    with db.session() as session:
        assert repo.delete_expired(session) >= 1
        assert repo.get_job(session, job_id) is None
    db.dispose()


def test_full_api_lifecycle_on_postgres():
    with TestClient(make_app(FakeRunner(), database_url=DATABASE_URL)) as client:
        assert (
            client.get("/api/health/ready").json()["checks"][0]["detail"].startswith("postgresql")
        )
        topic = f"postgres lifecycle {secrets.token_hex(4)}"
        job = client.post("/api/v1/research", json={"topic": topic}).json()
        final = wait_for_status(client, job["id"], {"succeeded"})
        assert final["result_available"]
        result = client.get(f"/api/v1/research/{job['id']}/result").json()
        assert result["sources"][0]["url"] == "https://docs.example.org/guide"
        with client.stream("GET", f"/api/v1/research/{job['id']}/events") as stream:
            assert "event: end" in "".join(stream.iter_text())

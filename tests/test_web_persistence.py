"""Tests for the database layer, migrations, restart recovery, and cleanup."""

from __future__ import annotations

import ssl
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from research_team.web import repository as repo
from research_team.web.db import Database, normalize_database_url
from research_team.web.ratelimit import (
    ConcurrencyLimiter,
    SlidingWindowLimiter,
    client_ip,
    hash_client,
)
from research_team.web.settings import WebSettings
from tests.web_helpers import FakeRunner, make_app, wait_for_status


# --------------------------------------------------------------------------- #
# Database URLs
# --------------------------------------------------------------------------- #
def test_postgres_urls_use_pg8000_and_tls():
    url, args = normalize_database_url(
        "postgres://user:pw@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+pg8000://user:pw@ep-x.neon.tech/db"
    assert isinstance(args["ssl_context"], ssl.SSLContext)


def test_sqlite_urls_pass_through():
    assert normalize_database_url("sqlite:///./data/x.db") == ("sqlite:///./data/x.db", {})


def test_migrations_create_schema_on_file_database(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'nested' / 'app.db'}")
    db.migrate()
    db.migrate()  # idempotent
    assert db.ping()
    with db.session() as session:
        job = repo.create_job(
            session,
            id="a" * 32,
            topic="t",
            instructions=None,
            depth="quick",
            report_style="technical_report",
            model="m",
            cache_key="c",
            owner_token_hash="h",
            client_hash="ip",
            idempotency_key=None,
            expires_at=repo.utcnow() + timedelta(days=1),
        )
        repo.add_event(session, job.id, "queued", None, "queued", {})
    with db.session() as session:
        assert repo.get_job(session, "a" * 32).status == "queued"
        assert len(repo.list_events(session, "a" * 32)) == 1
    db.dispose()


# --------------------------------------------------------------------------- #
# Recovery and cleanup
# --------------------------------------------------------------------------- #
def _insert(db: Database, job_id: str, status: str, *, expires_in_days: float = 1) -> None:
    with db.session() as session:
        job = repo.create_job(
            session,
            id=job_id,
            topic="recovery topic",
            instructions=None,
            depth="quick",
            report_style="technical_report",
            model="openai/gpt-oss-120b",
            cache_key=job_id,
            owner_token_hash="h",
            client_hash="ip",
            idempotency_key=None,
            expires_at=repo.utcnow() + timedelta(days=expires_in_days),
        )
        job.status = status
        repo.add_event(session, job_id, "queued", None, "queued", {})


def test_restart_recovery_fails_running_and_resumes_queued(tmp_path):
    url = f"sqlite:///{tmp_path / 'recovery.db'}"
    db = Database(url)
    db.migrate()
    _insert(db, "1" * 32, "running")
    _insert(db, "2" * 32, "queued")
    db.dispose()

    runner = FakeRunner()
    with TestClient(make_app(runner, database_url=url)) as client:
        interrupted = client.get(f"/api/v1/research/{'1' * 32}/status").json()
        assert interrupted["status"] == "failed"
        assert interrupted["error"]["code"] == "interrupted"
        resumed = wait_for_status(client, "2" * 32, {"succeeded"})
        assert resumed["result_available"] is True
    assert [call["topic"] for call in runner.calls] == ["recovery topic"]


def test_cleanup_deletes_only_expired_finished_jobs(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'cleanup.db'}")
    db.migrate()
    _insert(db, "3" * 32, "succeeded", expires_in_days=-1)
    _insert(db, "4" * 32, "queued", expires_in_days=-1)  # active: kept
    _insert(db, "5" * 32, "failed", expires_in_days=1)  # not expired: kept
    with db.session() as session:
        repo.save_result(session, "3" * 32, {"report_markdown": "x"})
    with db.session() as session:
        assert repo.delete_expired(session) == 1
    with db.session() as session:
        assert repo.get_job(session, "3" * 32) is None
        assert repo.get_result(session, "3" * 32) is None
        assert repo.list_events(session, "3" * 32) == []
        assert repo.get_job(session, "4" * 32) is not None
        assert repo.get_job(session, "5" * 32) is not None
    db.dispose()


def test_state_transitions_never_go_backwards(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'states.db'}")
    db.migrate()
    _insert(db, "6" * 32, "queued")
    with db.session() as session:
        assert repo.cancel_if_queued(session, "6" * 32) is True
    with db.session() as session:
        assert repo.mark_running(session, "6" * 32) is False  # cancelled job stays cancelled
        assert repo.get_job(session, "6" * 32).status == "cancelled"
    db.dispose()


# --------------------------------------------------------------------------- #
# Rate limiting primitives
# --------------------------------------------------------------------------- #
def test_sliding_window_limiter():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10)
    assert limiter.hit("a", now=0) == (True, 0)
    assert limiter.hit("a", now=1) == (True, 0)
    allowed, retry_after = limiter.hit("a", now=2)
    assert not allowed and retry_after == 8
    assert limiter.hit("b", now=2) == (True, 0)  # independent keys
    assert limiter.hit("a", now=10.5) == (True, 0)  # window slid


def test_concurrency_limiter():
    limiter = ConcurrencyLimiter(limit=1)
    assert limiter.acquire("x")
    assert not limiter.acquire("x")
    limiter.release("x")
    assert limiter.acquire("x")


@pytest.mark.parametrize(
    ("peer", "xff", "hops", "expected"),
    [
        ("10.0.0.1", "1.1.1.1", 0, "10.0.0.1"),  # header ignored unless proxies are trusted
        ("10.0.0.1", "6.6.6.6, 1.1.1.1", 1, "1.1.1.1"),  # spoofed left-most entry ignored
        ("10.0.0.1", "1.1.1.1, 2.2.2.2", 2, "1.1.1.1"),
        ("10.0.0.1", "1.1.1.1", 2, "10.0.0.1"),  # chain shorter than declared hops
        (None, None, 0, "unknown"),
    ],
)
def test_client_ip_resolution(peer, xff, hops, expected):
    assert client_ip(peer, xff, hops) == expected


def test_client_hash_is_salted_and_not_reversible():
    assert hash_client("1.1.1.1", "a") != hash_client("1.1.1.1", "b")
    assert "1.1.1.1" not in hash_client("1.1.1.1", "a")


# --------------------------------------------------------------------------- #
# Settings validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "overrides",
    [
        {"max_concurrent_jobs": 0},
        {"max_concurrent_jobs": 50},
        {"cors_origins": ("*",)},
        {"trusted_proxy_hops": -1},
        {"database_url": " "},
    ],
)
def test_invalid_web_settings_raise(overrides):
    from research_team.exceptions import ConfigError

    with pytest.raises(ConfigError):
        WebSettings(**overrides)


def test_web_settings_from_env(monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_JOBS", "2")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("ALLOWED_MODELS", "openai/gpt-oss-20b")
    settings = WebSettings.from_env()
    assert settings.max_concurrent_jobs == 2
    assert settings.cors_origins == ("https://a.example", "https://b.example")
    assert settings.allowed_models == ("openai/gpt-oss-20b",)
    assert "salt" not in repr(settings)


def test_shutdown_marks_running_jobs_interrupted_not_cancelled(tmp_path):
    import threading

    gate = threading.Event()
    url = f"sqlite:///{tmp_path / 'shutdown.db'}"
    client = TestClient(make_app(FakeRunner(gate=gate), database_url=url))
    with client:
        job = client.post("/api/v1/research", json={"topic": "shutdown topic"}).json()
        wait_for_status(client, job["id"], {"running"})
    # Leaving the context runs the lifespan shutdown, which stops running jobs.
    db = Database(url)
    with db.session() as session:
        stored = repo.get_job(session, job["id"])
        assert stored.status == "failed"
        assert stored.error_code == "interrupted"
    db.dispose()

"""Integration tests: HTTP API -> job runner -> persistence -> SSE/downloads."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from research_team import __version__
from research_team.exceptions import (
    ProviderUnavailableError,
    RateLimitExceededError,
)
from tests.web_helpers import FakeRunner, make_app, wait_for_status

TOPIC = {"topic": "Vector databases for retrieval augmented generation", "depth": "quick"}


@pytest.fixture
def runner():
    return FakeRunner()


@pytest.fixture
def client(runner):
    with TestClient(make_app(runner)) as test_client:
        yield test_client


def _create(client, body=TOPIC, **headers):
    return client.post("/api/v1/research", json=body, headers=headers)


# --------------------------------------------------------------------------- #
# Health & metadata
# --------------------------------------------------------------------------- #
def test_health_and_security_headers(client):
    response = client.get("/api/health")
    assert response.json() == {"status": "ok", "version": __version__}
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in headers["content-security-policy"]
    assert len(headers["x-request-id"]) >= 8


def test_request_id_is_propagated_when_safe(client):
    assert (
        client.get("/api/health", headers={"X-Request-ID": "abc12345"}).headers["x-request-id"]
        == "abc12345"
    )
    assert (
        client.get("/api/health", headers={"X-Request-ID": "bad id!"}).headers["x-request-id"]
        != "bad id!"
    )


def test_readiness_reports_checks(client, monkeypatch):
    from research_team.web.health import CheckResult, ProviderHealth

    monkeypatch.setattr(
        ProviderHealth, "check", lambda self, config, model: CheckResult("llm:groq", True, "ok")
    )
    body = client.get("/api/health/ready").json()
    assert body["status"] == "ready"
    assert {c["name"] for c in body["checks"]} >= {"database", "configuration", "job_runner"}


def test_readiness_unavailable_without_engine_config():
    from research_team.web.app import create_app
    from tests.web_helpers import make_settings

    app = create_app(make_settings(), runner=FakeRunner())
    app.state.web.config = None
    with TestClient(app) as test_client:
        response = test_client.get("/api/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"
        create = _create(test_client)
        assert create.status_code == 503
        assert create.json()["error"]["code"] == "not_configured"


def test_meta_exposes_models_and_limits(client):
    body = client.get("/api/v1/meta").json()
    assert body["models"][0] == {"id": "openai/gpt-oss-120b", "provider": "groq", "default": True}
    assert body["depths"] == ["quick", "standard", "deep"]
    assert body["limits"]["max_topic_chars"] == 300
    assert body["persistence"] == "ephemeral"
    assert body["search_providers"] == ["serper"]
    assert body["api_docs"] is True


def test_meta_reports_disabled_api_docs():
    with TestClient(make_app(enable_api_docs=False)) as client:
        assert client.get("/api/v1/meta").json()["api_docs"] is False
        assert client.get("/api/docs").status_code == 404


# --------------------------------------------------------------------------- #
# Job lifecycle
# --------------------------------------------------------------------------- #
def test_full_job_lifecycle(client, runner):
    created = _create(client)
    assert created.status_code == 202
    job = created.json()
    assert job["status"] == "queued"
    assert job["owner_token"]
    assert created.headers["location"] == f"/api/v1/research/{job['id']}"

    final = wait_for_status(client, job["id"], {"succeeded"})
    assert [s["status"] for s in final["stages"]] == ["completed"] * 3
    assert final["stages"][0]["searches"] == 1
    assert final["stages"][0]["llm_calls"] == 1
    assert final["result_available"] is True
    assert final["started_at"] and final["finished_at"]

    detail = client.get(f"/api/v1/research/{job['id']}").json()
    assert detail["result"]["report_markdown"].startswith("# Report")
    assert detail["result"]["sources"][0]["url"] == "https://docs.example.org/guide"
    assert detail["result"]["token_usage"] == {"total_tokens": 99}

    result = client.get(f"/api/v1/research/{job['id']}/result")
    assert result.status_code == 200
    assert runner.calls[0]["options"].depth == "quick"
    assert runner.calls[0]["options"].model == "openai/gpt-oss-120b"


def test_sse_stream_replays_events_and_ends(client):
    job = _create(client).json()
    wait_for_status(client, job["id"], {"succeeded"})
    with client.stream("GET", f"/api/v1/research/{job['id']}/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        body = "".join(stream.iter_text())
    assert body.startswith("retry: 3000")
    assert '"type":"stage_started"' in body
    assert '"type":"search"' in body
    assert body.rstrip().endswith('data: {"status": "succeeded"}')

    # Resuming after the last seen id only sends newer events.
    last_id = int(body.split("id: ")[-1].split("\n")[0])
    with client.stream(
        "GET", f"/api/v1/research/{job['id']}/events", headers={"Last-Event-ID": str(last_id)}
    ) as stream:
        resumed = "".join(stream.iter_text())
    assert "id: " not in resumed
    assert "event: end" in resumed


def test_downloads(client):
    job = _create(client).json()
    wait_for_status(client, job["id"], {"succeeded"})
    markdown = client.get(f"/api/v1/research/{job['id']}/download")
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert (
        'filename="research-vector-databases-for-retrieval-augmented-generation-'
        in (markdown.headers["content-disposition"])
    )
    assert "## Sources Retrieved During Research" in markdown.text
    as_json = client.get(f"/api/v1/research/{job['id']}/download?format=json")
    assert as_json.json()["job_id"] == job["id"]
    assert client.get(f"/api/v1/research/{job['id']}/download?format=exe").status_code == 422


def test_result_not_ready_returns_409():
    gate = threading.Event()
    with TestClient(make_app(FakeRunner(gate=gate))) as client:
        job = _create(client).json()
        wait_for_status(client, job["id"], {"running"})
        response = client.get(f"/api/v1/research/{job['id']}/result")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "not_ready"
        gate.set()
        wait_for_status(client, job["id"], {"succeeded"})


# --------------------------------------------------------------------------- #
# Cancellation & ownership
# --------------------------------------------------------------------------- #
def test_cancel_running_job_requires_owner_token():
    gate = threading.Event()
    with TestClient(make_app(FakeRunner(gate=gate))) as client:
        job = _create(client).json()
        wait_for_status(client, job["id"], {"running"})

        forbidden = client.post(
            f"/api/v1/research/{job['id']}/cancel", headers={"X-Owner-Token": "wrong"}
        )
        assert forbidden.status_code == 403

        accepted = client.post(
            f"/api/v1/research/{job['id']}/cancel", headers={"X-Owner-Token": job["owner_token"]}
        )
        assert accepted.status_code == 202
        final = wait_for_status(client, job["id"], {"cancelled"})
        assert final["error"]["code"] == "cancelled"
        assert final["stages"][0]["status"] == "cancelled"
        assert final["stages"][1]["status"] == "pending"

        again = client.post(
            f"/api/v1/research/{job['id']}/cancel", headers={"X-Owner-Token": job["owner_token"]}
        )
        assert again.status_code == 409


def test_cancel_queued_job_never_runs():
    gate = threading.Event()
    runner = FakeRunner(gate=gate)
    with TestClient(make_app(runner, max_concurrent_jobs=1)) as client:
        first = _create(client).json()
        wait_for_status(client, first["id"], {"running"})
        second = _create(client, {**TOPIC, "topic": "A different topic entirely"}).json()
        assert client.get(f"/api/v1/research/{second['id']}/status").json()["queue_position"] == 1

        cancelled = client.post(
            f"/api/v1/research/{second['id']}/cancel",
            headers={"X-Owner-Token": second["owner_token"]},
        ).json()
        assert cancelled["status"] == "cancelled"
        gate.set()
        wait_for_status(client, first["id"], {"succeeded"})
        assert len(runner.calls) == 1


# --------------------------------------------------------------------------- #
# Failures surface safe, typed errors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("error", "code"),
    [
        (RateLimitExceededError("429 from provider: secret details"), "rate_limited"),
        (ProviderUnavailableError("upstream exploded"), "provider_unavailable"),
        (RuntimeError("internal stack details"), "internal_error"),
    ],
)
def test_failures_are_reported_without_leaking_internals(error, code):
    with TestClient(make_app(FakeRunner(error=error))) as client:
        job = _create(client).json()
        final = wait_for_status(client, job["id"], {"failed"})
        assert final["error"]["code"] == code
        assert "secret details" not in final["error"]["message"]
        assert "stack details" not in final["error"]["message"]
        assert final["stages"][0]["status"] == "failed"


# --------------------------------------------------------------------------- #
# Validation, dedup, caching, quotas
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"topic": "ab"}, "invalid_request"),
        ({"topic": "x" * 301}, "topic_too_long"),
        ({"topic": "valid topic", "instructions": "y" * 1001}, "instructions_too_long"),
        ({"topic": "valid topic", "model": "gpt-9-ultra"}, "invalid_model"),
        ({"topic": "valid topic", "depth": "bottomless"}, "invalid_request"),
        ({"topic": "valid topic", "unexpected": 1}, "invalid_request"),
        ({"topic": "  <b></b>  "}, "invalid_topic"),
    ],
)
def test_invalid_requests_are_rejected(client, body, code):
    response = _create(client, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_unknown_and_malformed_ids_return_404(client):
    assert client.get("/api/v1/research/not-a-real-id").status_code == 404
    assert client.get("/api/v1/research/" + "a" * 32).json()["error"]["code"] == "not_found"
    assert client.get("/api/v1/research/" + "a" * 32 + "/events").status_code == 404


def test_body_size_limit(client):
    response = client.post(
        "/api/v1/research",
        content=b'{"topic": "' + b"x" * 20_000 + b'"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_idempotency_key_returns_same_job(client):
    first = _create(client, **{"Idempotency-Key": "key-12345678"})
    second = _create(
        client, {**TOPIC, "topic": "something else"}, **{"Idempotency-Key": "key-12345678"}
    )
    assert first.status_code == 202 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["owner_token"] is None
    assert _create(client, **{"Idempotency-Key": "bad key"}).status_code == 422


def test_identical_request_is_served_from_cache():
    runner = FakeRunner()
    with TestClient(make_app(runner, result_cache_ttl_hours=24)) as client:
        first = _create(client).json()
        wait_for_status(client, first["id"], {"succeeded"})
        again = _create(client, {**TOPIC, "topic": TOPIC["topic"].upper()})
        assert again.status_code == 200
        assert again.json()["cached"] is True
        assert again.json()["id"] == first["id"]
        assert len(runner.calls) == 1


def test_per_ip_hourly_quota():
    with TestClient(make_app(jobs_per_ip_per_hour=2)) as client:
        for index in range(2):
            assert _create(client, {"topic": f"topic number {index}"}).status_code == 202
        blocked = _create(client, {"topic": "one too many"})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "hourly_limit"
        assert blocked.headers["retry-after"] == "3600"


def test_global_daily_quota():
    with TestClient(make_app(global_jobs_per_day=1)) as client:
        assert _create(client).status_code == 202
        blocked = _create(client, {"topic": "another topic here"})
        assert blocked.json()["error"]["code"] == "global_daily_limit"


def test_queue_capacity():
    gate = threading.Event()
    with TestClient(make_app(FakeRunner(gate=gate), max_queued_jobs=1)) as client:
        running = _create(client).json()
        wait_for_status(client, running["id"], {"running"})
        assert _create(client, {"topic": "queued topic one"}).status_code == 202
        full = _create(client, {"topic": "queued topic two"})
        assert full.status_code == 503
        assert full.json()["error"]["code"] == "server_busy"
        gate.set()


def test_api_rate_limit_per_ip():
    with TestClient(make_app(api_requests_per_ip_per_minute=3)) as client:
        codes = [client.get("/api/v1/meta").status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        # Health checks are exempt so the platform can always probe the app.
        assert client.get("/api/health").status_code == 200


def test_usage_endpoint_counts_callers_jobs(client):
    _create(client)
    usage = client.get("/api/v1/usage").json()
    assert usage["jobs_today"] == 1
    assert usage["jobs_per_ip_per_day"] == 10


def test_cors_is_closed_by_default_and_explicit_when_configured():
    with TestClient(make_app()) as client:
        response = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in response.headers
    with TestClient(make_app(cors_origins=("https://app.example",))) as client:
        allowed = client.get("/api/health", headers={"Origin": "https://app.example"})
        assert allowed.headers["access-control-allow-origin"] == "https://app.example"
        denied = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in denied.headers


def test_openapi_documents_versioned_routes(client):
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/api/v1/research" in paths
    assert "/api/v1/research/{job_id}/events" in paths
    assert "/api/health/ready" in paths

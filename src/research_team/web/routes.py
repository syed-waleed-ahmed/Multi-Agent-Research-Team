"""HTTP routes for the public API.

Endpoint map
------------
Unversioned infrastructure endpoints:

* ``GET  /api/health``        — liveness (process is up)
* ``GET  /api/health/ready``  — readiness (database, configuration, provider)

Versioned resource endpoints (``/api/v1``):

* ``GET  /meta``                       — public configuration for the UI
* ``GET  /usage``                      — the caller's remaining quota
* ``POST /research``                   — submit a research job (202)
* ``GET  /research/{id}``              — job details (+ result when finished)
* ``GET  /research/{id}/status``       — lightweight status for polling
* ``GET  /research/{id}/events``       — live progress (Server-Sent Events)
* ``GET  /research/{id}/result``       — final result (409 until it succeeds)
* ``POST /research/{id}/cancel``       — cancel (requires ``X-Owner-Token``)
* ``GET  /research/{id}/download``     — Markdown or JSON download

Access model: job ids are unguessable (128-bit random), so a job URL acts as a
private share link. Cancelling additionally requires the owner token that was
returned (once) at creation; only its SHA-256 hash is stored.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from .. import __version__
from ..config import DEFAULT_GROQ_MODELS, AppConfig
from ..tasks import sanitize_user_text
from . import repository as repo
from .db import Database
from .health import ProviderHealth
from .jobs import JobManager
from .models import ResearchJob
from .ratelimit import ConcurrencyLimiter, client_ip, hash_client
from .schemas import (
    Depth,
    EventOut,
    HealthOut,
    JobCreated,
    JobDetail,
    JobError,
    JobOptions,
    JobOut,
    JobStatus,
    LimitsOut,
    MetaOut,
    ModelOut,
    ReadinessCheck,
    ReadinessOut,
    ReportStyle,
    ResearchCreate,
    ResultOut,
    StageOut,
    UsageOut,
)
from .settings import WebSettings

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,100}$")
_SSE_POLL_SECONDS = 1.0
_SSE_HEARTBEAT_SECONDS = 15.0


class ApiError(Exception):
    """An error rendered as ``{"error": {...}}`` with a stable code."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


@dataclass
class WebState:
    """Process-wide objects shared by request handlers."""

    settings: WebSettings
    db: Database
    jobs: JobManager
    streams: ConcurrencyLimiter
    provider_health: ProviderHealth
    config: AppConfig | None
    config_error: str | None

    def require_config(self) -> AppConfig:
        if self.config is None:
            raise ApiError(
                503,
                "not_configured",
                "The research engine is not configured on this server yet.",
            )
        return self.config


def _state(request: Request) -> WebState:
    state: WebState = request.app.state.web
    return state


def _client_hash(request: Request, state: WebState) -> str:
    ip = client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        state.settings.trusted_proxy_hops,
    )
    return hash_client(ip, state.settings.ip_hash_salt)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Model helpers
# --------------------------------------------------------------------------- #
def available_models(config: AppConfig | None, settings: WebSettings) -> list[ModelOut]:
    """The models a visitor may choose (operator allowlist, else provider defaults)."""
    if config is None:
        return []
    provider = config.llm_provider
    default = {
        "groq": config.groq_model,
        "gemini": config.gemini_model,
        "openrouter": config.openrouter_model,
        "openai_compatible": config.openai_compatible_model,
        "ollama": config.ollama_model,
    }[provider]
    if settings.allowed_models:
        ids = list(settings.allowed_models)
    elif provider == "groq":
        ids = list(DEFAULT_GROQ_MODELS)
    else:
        ids = [default]
    if default not in ids:
        ids.insert(0, default)
    return [ModelOut(id=model, provider=provider, default=model == default) for model in ids]


def _job_out(session: Any, job: ResearchJob, *, cached: bool = False) -> dict[str, Any]:
    has_result = job.status == JobStatus.SUCCEEDED.value
    return {
        "id": job.id,
        "status": JobStatus(job.status),
        "topic": job.topic,
        "options": JobOptions(
            depth=Depth(job.depth),
            report_style=ReportStyle(job.report_style),
            model=job.model,
            instructions=job.instructions,
        ),
        "stages": [StageOut(**stage) for stage in job.stages],
        "created_at": repo.as_utc(job.created_at),
        "started_at": repo.as_utc(job.started_at),
        "finished_at": repo.as_utc(job.finished_at),
        "queue_position": repo.queue_position(session, job),
        "error": (
            JobError(code=job.error_code, message=job.error_message or "")
            if job.error_code
            else None
        ),
        "cached": cached,
        "result_available": has_result,
    }


def _result_out(job: ResearchJob, payload: dict[str, Any], created_at: Any) -> ResultOut:
    return ResultOut(job_id=job.id, topic=job.topic, created_at=repo.utc(created_at), **payload)


def _load_job(state: WebState, job_id: str) -> tuple[ResearchJob, dict[str, Any]]:
    if not _JOB_ID.match(job_id):
        raise ApiError(404, "not_found", "Research job not found.")
    with state.db.session() as session:
        job = repo.get_job(session, job_id)
        if job is None:
            raise ApiError(404, "not_found", "Research job not found.")
        return job, _job_out(session, job)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].rstrip("-") or "research"


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
health_router = APIRouter(prefix="/api/health", tags=["health"])


@health_router.get("", response_model=HealthOut, summary="Liveness probe")
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@health_router.get(
    "/ready",
    response_model=ReadinessOut,
    summary="Readiness probe",
    responses={503: {"model": ReadinessOut}},
)
def readiness(request: Request, response: Response) -> ReadinessOut:
    state = _state(request)
    checks = [
        ReadinessCheck(
            name="database",
            ok=state.db.ping(),
            detail=f"{state.db.dialect} ({state.db.persistence})",
        ),
        ReadinessCheck(
            name="configuration",
            ok=state.config is not None,
            detail="ok" if state.config is not None else (state.config_error or "invalid"),
        ),
        ReadinessCheck(
            name="job_runner",
            ok=state.jobs.healthy,
            detail="running" if state.jobs.healthy else "stopped",
        ),
    ]
    if state.config is not None:
        models = available_models(state.config, state.settings)
        default_model = next((m.id for m in models if m.default), "")
        probe = state.provider_health.check(state.config, default_model)
        checks.append(ReadinessCheck(name=probe.name, ok=probe.ok, detail=probe.detail))
        searches = [
            name
            for name in state.config.search_providers
            if (name == "serper" and state.config.serper_api_key)
            or (name == "tavily" and state.config.tavily_api_key)
        ]
        checks.append(
            ReadinessCheck(
                name="search",
                ok=bool(searches),
                detail=f"configured: {', '.join(searches)} (not probed to save quota)",
            )
        )
    critical = {"database", "configuration", "job_runner"}
    if all(c.ok for c in checks if c.name in critical):
        status = "ready" if all(c.ok for c in checks) else "degraded"
    else:
        status = "unavailable"
        response.status_code = 503
    return ReadinessOut(status=status, version=__version__, checks=checks)


# --------------------------------------------------------------------------- #
# Research API
# --------------------------------------------------------------------------- #
router = APIRouter(prefix="/api/v1", tags=["research"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "Job not found"},
    429: {"description": "Rate limit or quota exceeded"},
}


@router.get("/meta", response_model=MetaOut, summary="Public configuration for clients")
def meta(request: Request) -> MetaOut:
    state = _state(request)
    settings = state.settings
    config = state.config
    searches: list[str] = []
    if config is not None:
        searches = [
            name
            for name in config.search_providers
            if (name == "serper" and config.serper_api_key)
            or (name == "tavily" and config.tavily_api_key)
        ]
    return MetaOut(
        version=__version__,
        repository_url=settings.repository_url,
        models=available_models(config, settings),
        search_providers=searches,
        depths=list(Depth),
        report_styles=list(ReportStyle),
        limits=LimitsOut(
            max_topic_chars=settings.max_topic_chars,
            max_instructions_chars=settings.max_instructions_chars,
            jobs_per_ip_per_hour=settings.jobs_per_ip_per_hour,
            jobs_per_ip_per_day=settings.jobs_per_ip_per_day,
            global_jobs_per_day=settings.global_jobs_per_day,
            job_timeout_seconds=settings.job_timeout_seconds,
            max_concurrent_jobs=settings.max_concurrent_jobs,
        ),
        persistence=state.db.persistence,
        api_docs=settings.enable_api_docs,
    )


@router.get("/usage", response_model=UsageOut, summary="The caller's remaining quota")
def usage(request: Request) -> UsageOut:
    state = _state(request)
    client = _client_hash(request, state)
    day_ago = repo.utcnow() - timedelta(days=1)
    with state.db.session() as session:
        return UsageOut(
            jobs_today=repo.count_created(session, day_ago, client),
            jobs_per_ip_per_day=state.settings.jobs_per_ip_per_day,
            global_jobs_today=repo.count_created(session, day_ago),
            global_jobs_per_day=state.settings.global_jobs_per_day,
            active_jobs=repo.count_status(session, [JobStatus.RUNNING.value]),
            max_concurrent_jobs=state.settings.max_concurrent_jobs,
            queued_jobs=repo.count_status(session, [JobStatus.QUEUED.value]),
            max_queued_jobs=state.settings.max_queued_jobs,
        )


def _validate_request(body: ResearchCreate, state: WebState, config: AppConfig) -> dict[str, Any]:
    settings = state.settings
    topic = sanitize_user_text(body.topic, settings.max_topic_chars + 1)
    if len(topic) < 3:
        raise ApiError(422, "invalid_topic", "Please enter a topic of at least 3 characters.")
    if len(topic) > settings.max_topic_chars:
        raise ApiError(
            422,
            "topic_too_long",
            f"Topics are limited to {settings.max_topic_chars} characters.",
        )
    instructions = sanitize_user_text(body.instructions, settings.max_instructions_chars + 1)
    if len(instructions) > settings.max_instructions_chars:
        raise ApiError(
            422,
            "instructions_too_long",
            f"Instructions are limited to {settings.max_instructions_chars} characters.",
        )
    models = available_models(config, settings)
    model = body.model or next(m.id for m in models if m.default)
    if model not in {m.id for m in models}:
        raise ApiError(422, "invalid_model", "That model is not available on this server.")
    normalized = {
        "topic": topic.lower(),
        "instructions": instructions.lower(),
        "depth": body.depth.value,
        "report_style": body.report_style.value,
        "model": model,
    }
    return {
        "topic": topic,
        "instructions": instructions or None,
        "depth": body.depth.value,
        "report_style": body.report_style.value,
        "model": model,
        "cache_key": _sha256(json.dumps(normalized, sort_keys=True)),
    }


@router.post(
    "/research",
    status_code=202,
    response_model=JobCreated,
    summary="Submit a research job",
    responses={
        200: {"model": JobCreated, "description": "Existing or cached job returned"},
        422: {"description": "Invalid request"},
        429: {"description": "Quota exceeded"},
        503: {"description": "Server busy or not configured"},
    },
)
def create_research(
    body: ResearchCreate,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobCreated:
    state = _state(request)
    config = state.require_config()
    settings = state.settings
    fields = _validate_request(body, state, config)
    client = _client_hash(request, state)
    if idempotency_key is not None and not _IDEMPOTENCY_KEY.match(idempotency_key):
        raise ApiError(422, "invalid_idempotency_key", "Idempotency-Key has an invalid format.")
    now = repo.utcnow()

    with state.jobs.create_lock, state.db.session() as session:
        # 1. Same client retried the same request (network retry, double click).
        existing = (
            repo.find_idempotent(session, client, idempotency_key, now - timedelta(days=1))
            if idempotency_key
            else None
        ) or repo.find_active_duplicate(session, client, fields["cache_key"])
        if existing is not None:
            response.status_code = 200
            return JobCreated(**_job_out(session, existing))

        # 2. Identical request already answered recently: reuse it, spend no quota.
        if settings.result_cache_ttl_hours > 0:
            cached = repo.find_cached(
                session, fields["cache_key"], now - timedelta(hours=settings.result_cache_ttl_hours)
            )
            if cached is not None:
                response.status_code = 200
                return JobCreated(**_job_out(session, cached, cached=True))

        # 3. Quotas (counted from the database).
        hour_ago, day_ago = now - timedelta(hours=1), now - timedelta(days=1)
        if repo.count_created(session, hour_ago, client) >= settings.jobs_per_ip_per_hour:
            raise ApiError(
                429,
                "hourly_limit",
                f"You can start {settings.jobs_per_ip_per_hour} research runs per hour. "
                "Please try again later.",
                retry_after=3600,
            )
        if repo.count_created(session, day_ago, client) >= settings.jobs_per_ip_per_day:
            raise ApiError(
                429,
                "daily_limit",
                f"You have reached the daily limit of {settings.jobs_per_ip_per_day} research "
                "runs. This keeps the free service available for everyone.",
                retry_after=86400,
            )
        if repo.count_created(session, day_ago) >= settings.global_jobs_per_day:
            raise ApiError(
                429,
                "global_daily_limit",
                "This free instance has reached its daily research capacity. "
                "Please try again tomorrow, or self-host it with your own free API keys.",
                retry_after=3600,
            )
        queued = repo.count_status(session, [JobStatus.QUEUED.value])
        if queued >= settings.max_queued_jobs:
            raise ApiError(
                503,
                "server_busy",
                "The research queue is full right now. Please try again in a few minutes.",
                retry_after=120,
            )

        owner_token = secrets.token_urlsafe(24)
        job = repo.create_job(
            session,
            id=secrets.token_hex(16),
            owner_token_hash=_sha256(owner_token),
            client_hash=client,
            idempotency_key=idempotency_key,
            expires_at=state.jobs.expires_at(),
            **fields,
        )
        repo.add_event(session, job.id, "queued", None, "Research job queued", {})
        payload = _job_out(session, job)

    state.jobs.submit(payload["id"])
    response.headers["Location"] = f"/api/v1/research/{payload['id']}"
    return JobCreated(**payload, owner_token=owner_token)


@router.get(
    "/research/{job_id}",
    response_model=JobDetail,
    summary="Job details, including the result once finished",
    responses=_ERRORS,
)
def get_research(job_id: str, request: Request) -> JobDetail:
    state = _state(request)
    job, out = _load_job(state, job_id)
    result = None
    if out["result_available"]:
        with state.db.session() as session:
            row = repo.get_result(session, job_id)
            if row is not None:
                result = _result_out(job, row.payload, row.created_at)
    return JobDetail(**out, result=result)


@router.get(
    "/research/{job_id}/status",
    response_model=JobOut,
    summary="Lightweight job status for polling",
    responses=_ERRORS,
)
def get_status(job_id: str, request: Request) -> JobOut:
    _, out = _load_job(_state(request), job_id)
    return JobOut(**out)


@router.get(
    "/research/{job_id}/result",
    response_model=ResultOut,
    summary="Final result",
    responses={**_ERRORS, 409: {"description": "Job has not succeeded (yet)"}},
)
def get_result(job_id: str, request: Request) -> ResultOut:
    state = _state(request)
    job, out = _load_job(state, job_id)
    with state.db.session() as session:
        row = repo.get_result(session, job_id) if out["result_available"] else None
    if row is None:
        raise ApiError(409, "not_ready", f"The job is {job.status}; no result is available.")
    return _result_out(job, row.payload, row.created_at)


@router.post(
    "/research/{job_id}/cancel",
    status_code=202,
    response_model=JobOut,
    summary="Cancel a queued or running job",
    responses={**_ERRORS, 403: {"description": "Missing/invalid owner token"}, 409: {}},
)
def cancel_research(
    job_id: str,
    request: Request,
    owner_token: str | None = Header(default=None, alias="X-Owner-Token"),
) -> JobOut:
    state = _state(request)
    job, out = _load_job(state, job_id)
    if not owner_token or not hmac.compare_digest(_sha256(owner_token), job.owner_token_hash):
        raise ApiError(403, "forbidden", "Only the creator of this job can cancel it.")
    if JobStatus(job.status).is_terminal:
        raise ApiError(409, "already_finished", f"The job already {job.status}.")
    state.jobs.cancel(job_id)
    _, out = _load_job(state, job_id)
    return JobOut(**out)


@router.get(
    "/research/{job_id}/download",
    summary="Download the report (Markdown or JSON)",
    responses={**_ERRORS, 409: {"description": "Job has not succeeded (yet)"}},
)
def download(
    job_id: str,
    request: Request,
    format: str = Query("md", pattern="^(md|json)$"),
) -> Response:
    result = get_result(job_id, request)
    name = f"research-{_slug(result.topic)}-{job_id[:8]}"
    if format == "json":
        return Response(
            result.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{name}.json"'},
        )
    return Response(
        result.document_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}.md"'},
    )


@router.get(
    "/research/{job_id}/events",
    summary="Live progress stream (Server-Sent Events)",
    response_class=StreamingResponse,
    responses={
        **_ERRORS,
        200: {"content": {"text/event-stream": {}}, "description": "SSE stream"},
    },
)
async def stream_events(
    job_id: str,
    request: Request,
    after: int = Query(0, ge=0, description="Only send events with a larger id"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    state = _state(request)
    await run_in_threadpool(_load_job, state, job_id)  # 404 for unknown jobs
    client = _client_hash(request, state)
    if not state.streams.acquire(client):
        raise ApiError(429, "too_many_streams", "Too many open progress streams.", retry_after=30)
    cursor = after
    if last_event_id and last_event_id.isdigit():
        cursor = max(cursor, int(last_event_id))

    def fetch(after_id: int) -> tuple[list[EventOut], str]:
        with state.db.session() as session:
            job = repo.get_job(session, job_id)
            rows = repo.list_events(session, job_id, after_id)
            events = [
                EventOut(
                    id=row.id,
                    type=row.type,
                    stage=row.stage,
                    message=row.message,
                    data=row.data or {},
                    timestamp=repo.utc(row.created_at),
                )
                for row in rows
            ]
            return events, job.status if job else JobStatus.FAILED.value

    async def generate() -> AsyncIterator[str]:
        nonlocal cursor
        deadline = time.monotonic() + state.settings.job_timeout_seconds + 300
        last_sent = time.monotonic()
        try:
            yield "retry: 3000\n\n"
            while time.monotonic() < deadline:
                if await request.is_disconnected():
                    break
                events, status = await run_in_threadpool(fetch, cursor)
                for event in events:
                    cursor = event.id
                    yield f"id: {event.id}\ndata: {event.model_dump_json()}\n\n"
                    last_sent = time.monotonic()
                if not events and JobStatus(status).is_terminal:
                    yield f"event: end\ndata: {json.dumps({'status': status})}\n\n"
                    break
                if time.monotonic() - last_sent > _SSE_HEARTBEAT_SECONDS:
                    yield ": keep-alive\n\n"
                    last_sent = time.monotonic()
                await asyncio.sleep(_SSE_POLL_SECONDS)
        finally:
            state.streams.release(client)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


__all__ = ["ApiError", "WebState", "health_router", "router"]

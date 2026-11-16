"""FastAPI application factory.

``create_app()`` wires settings, the database, the job runner, middleware,
error handling, API routes, and (when built) the React frontend into one ASGI
app. A single process therefore serves both the website and its API, which is
the simplest deployment that fits a free hosting tier.
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..config import AppConfig, load_environment
from ..exceptions import ConfigError
from ..logging_config import configure_logging, get_logger
from .db import Database
from .health import ProviderHealth
from .jobs import JobManager, Runner
from .middleware import SecurityMiddleware, request_id_var
from .ratelimit import ConcurrencyLimiter, SlidingWindowLimiter
from .routes import ApiError, WebState, health_router, router
from .settings import WebSettings

log = get_logger("web")

_DESCRIPTION = """
Public API of the **Multi-Agent Research Team** platform.

Submit a topic, follow three AI agents (Research → Coding → Manager) in real time
over Server-Sent Events, and download the final Markdown report.

All limits are enforced per client IP and globally to protect shared free-tier
quotas; see `GET /api/v1/meta` for the active values.
"""


def _error(status: int, code: str, message: str, retry_after: int | None = None) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id_var.get(),
                "retry_after_seconds": retry_after,
            }
        },
        headers=headers,
    )


def _load_engine_config() -> tuple[AppConfig | None, str | None]:
    try:
        return AppConfig.from_env(load_dotenv_file=False), None
    except ConfigError as exc:
        log.error("Research engine is not configured: %s", exc)
        return None, str(exc)


def create_app(
    settings: WebSettings | None = None,
    *,
    config: AppConfig | None = None,
    runner: Runner | None = None,
    config_factory: Callable[[], AppConfig] | None = None,
    warm_up: bool | None = None,
) -> FastAPI:
    """Build the ASGI application.

    Parameters are injectable for tests and embedding; by default everything is
    read from the environment (and a local ``.env`` file, if present).
    ``warm_up`` pre-imports the agent stack at startup; it defaults to on when
    the real engine is used (no injected ``runner``).
    """
    if warm_up is None:
        warm_up = runner is None
    load_environment()
    settings = settings or WebSettings.from_env()
    config_error: str | None = None
    if config is None:
        config, config_error = _load_engine_config()
    if config is not None:
        configure_logging(config.normalized_log_level)
    else:
        configure_logging("INFO")

    db = Database(settings.database_url)
    resolved_config = config

    def _config() -> AppConfig:
        if resolved_config is None:
            raise ConfigError(config_error or "The research engine is not configured.")
        return resolved_config

    jobs = JobManager(
        db,
        settings,
        config_factory or _config,
        **({"runner": runner} if runner is not None else {}),
    )
    state = WebState(
        settings=settings,
        db=db,
        jobs=jobs,
        streams=ConcurrencyLimiter(settings.max_event_streams_per_ip),
        provider_health=ProviderHealth(),
        config=config,
        config_error=config_error,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.migrate()
        jobs.start()
        if warm_up:
            # Import the agent stack (~5 s, ~250 MB) in the background so the first
            # visitor's run starts immediately instead of waiting on imports.
            threading.Thread(target=_warm_up_engine, name="engine-warm-up", daemon=True).start()
        log.info(
            "Web app ready (v%s, db=%s/%s, workers=%d)",
            __version__,
            db.dialect,
            db.persistence,
            settings.max_concurrent_jobs,
        )
        try:
            yield
        finally:
            log.info("Shutting down: stopping job runner")
            jobs.shutdown()
            db.dispose()

    docs = settings.enable_api_docs
    app = FastAPI(
        title="Multi-Agent Research Team API",
        version=__version__,
        description=_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/docs" if docs else None,
        redoc_url="/api/redoc" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
    )
    app.state.web = state

    # --- middleware (last added = outermost) ---------------------------------
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Idempotency-Key", "X-Owner-Token", "Last-Event-ID"],
            expose_headers=["X-Request-ID", "Retry-After", "Location"],
            max_age=600,
        )
    app.add_middleware(
        SecurityMiddleware,
        max_body_bytes=settings.max_request_bytes,
        limiter=SlidingWindowLimiter(settings.api_requests_per_ip_per_minute, 60.0),
        trusted_proxy_hops=settings.trusted_proxy_hops,
        client_ip_headers=settings.client_ip_headers,
        ip_salt=settings.ip_hash_salt,
    )

    # --- error handling: stable envelopes, never leak internals --------------
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message, exc.retry_after)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ())[1:]) or "request"
        return _error(422, "invalid_request", f"Invalid {field}: {first.get('msg', 'invalid')}")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error (request %s)", request_id_var.get())
        return _error(500, "internal_error", "An unexpected server error occurred.")

    app.include_router(health_router)
    app.include_router(router)
    _mount_frontend(app, settings.static_dir)
    return app


def _warm_up_engine() -> None:
    try:
        import crewai  # noqa: F401
        import litellm  # noqa: F401

        log.info("Agent framework loaded")
    except Exception:  # pragma: no cover - a failed warm-up only costs latency later
        log.warning("Agent framework warm-up failed", exc_info=True)


def _mount_frontend(app: FastAPI, static_dir: Path | None) -> None:
    """Serve the built single-page app, with history-API fallback to index.html."""

    if static_dir is None:

        @app.get("/", include_in_schema=False)
        def _no_frontend() -> JSONResponse:
            return JSONResponse(
                {
                    "name": "Multi-Agent Research Team API",
                    "version": __version__,
                    "docs": "/api/docs",
                    "note": "Frontend not built. Run `npm run build` in ./frontend.",
                }
            )

        return

    root = static_dir.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def _spa(path: str) -> Response:
        if path.startswith("api/") or path == "api":
            return _error(404, "not_found", "Not found.")
        candidate = (root / path).resolve()
        # Path traversal guard: only files inside the build directory are served.
        if path and candidate.is_file() and candidate.is_relative_to(root):
            headers: dict[str, Any] = {}
            if candidate.parent.name == "assets":
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return FileResponse(candidate, headers=headers)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

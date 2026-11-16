"""Web-server settings: persistence, abuse limits, CORS, and static hosting.

Every limit that protects the shared free-tier quotas is configurable through
environment variables, with conservative defaults suitable for a single small
free instance. Settings are immutable and validated at startup so a bad value
fails fast instead of surfacing as a confusing runtime error.
"""

from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from ..config import _parse_int
from ..exceptions import ConfigError

_PACKAGE_DIR = Path(__file__).resolve().parent
_HEADER_NAME = re.compile(r"^[a-z0-9-]{1,64}$")


def _csv(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in (value or "").split(",") if item.strip())


def _bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_static_dir() -> Path | None:
    """Locate the built frontend (``frontend/dist``) in a source checkout or image."""
    for candidate in (
        Path(os.getenv("FRONTEND_DIST", "")) if os.getenv("FRONTEND_DIST") else None,
        _PACKAGE_DIR.parents[2] / "frontend" / "dist",
        Path.cwd() / "frontend" / "dist",
    ):
        if candidate is not None and (candidate / "index.html").is_file():
            return candidate
    return None


@dataclass(frozen=True)
class WebSettings:
    """Immutable configuration for the HTTP API and job runner."""

    database_url: str = "sqlite:///./data/research.db"
    #: Browser origins allowed to call the API cross-origin. Empty = same-origin only.
    cors_origins: tuple[str, ...] = ()
    #: Number of reverse proxies in front of the app whose X-Forwarded-For can be trusted.
    trusted_proxy_hops: int = 0
    #: Headers (lower-case) that a trusted edge proxy overwrites with the client IP,
    #: e.g. ("true-client-ip", "cf-connecting-ip") behind Cloudflare (as on Render).
    client_ip_headers: tuple[str, ...] = ()

    # --- job execution -----------------------------------------------------
    max_concurrent_jobs: int = 1
    max_queued_jobs: int = 5
    job_timeout_seconds: int = 600
    result_cache_ttl_hours: int = 24
    job_retention_days: int = 7

    # --- request validation --------------------------------------------------
    max_topic_chars: int = 300
    max_instructions_chars: int = 1000
    max_request_bytes: int = 16_384
    max_report_chars: int = 60_000

    # --- abuse protection ----------------------------------------------------
    jobs_per_ip_per_hour: int = 5
    jobs_per_ip_per_day: int = 10
    global_jobs_per_day: int = 100
    api_requests_per_ip_per_minute: int = 300
    max_event_streams_per_ip: int = 4
    #: Secret used to pseudonymise client IPs before they are stored.
    ip_hash_salt: str = field(default_factory=lambda: secrets.token_hex(16), repr=False)

    # --- presentation --------------------------------------------------------
    allowed_models: tuple[str, ...] = ()
    enable_api_docs: bool = True
    static_dir: Path | None = None
    repository_url: str = "https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team"

    def __post_init__(self) -> None:
        errors: list[str] = []
        positive = {
            "MAX_CONCURRENT_JOBS": self.max_concurrent_jobs,
            "JOB_TIMEOUT_SECONDS": self.job_timeout_seconds,
            "MAX_TOPIC_CHARS": self.max_topic_chars,
            "MAX_INSTRUCTIONS_CHARS": self.max_instructions_chars,
            "MAX_REQUEST_BYTES": self.max_request_bytes,
            "MAX_REPORT_CHARS": self.max_report_chars,
            "JOBS_PER_IP_PER_HOUR": self.jobs_per_ip_per_hour,
            "JOBS_PER_IP_PER_DAY": self.jobs_per_ip_per_day,
            "GLOBAL_JOBS_PER_DAY": self.global_jobs_per_day,
            "API_REQUESTS_PER_IP_PER_MINUTE": self.api_requests_per_ip_per_minute,
            "MAX_EVENT_STREAMS_PER_IP": self.max_event_streams_per_ip,
            "JOB_RETENTION_DAYS": self.job_retention_days,
        }
        errors += [f"{name} must be a positive integer." for name, v in positive.items() if v < 1]
        non_negative = {
            "MAX_QUEUED_JOBS": self.max_queued_jobs,
            "TRUSTED_PROXY_HOPS": self.trusted_proxy_hops,
            "RESULT_CACHE_TTL_HOURS": self.result_cache_ttl_hours,
        }
        errors += [f"{name} must be zero or greater." for name, v in non_negative.items() if v < 0]
        if self.max_concurrent_jobs > 8:
            errors.append("MAX_CONCURRENT_JOBS above 8 is not supported on a single instance.")
        if any(not _HEADER_NAME.match(name) for name in self.client_ip_headers):
            errors.append("CLIENT_IP_HEADERS must be a comma-separated list of header names.")
        if "*" in self.cors_origins:
            errors.append("CORS_ORIGINS must list explicit origins; '*' is not allowed.")
        if not self.database_url.strip():
            errors.append("DATABASE_URL must not be empty.")
        if errors:
            raise ConfigError(" ".join(errors))

    @classmethod
    def from_env(cls) -> WebSettings:
        env = os.getenv
        salt = env("IP_HASH_SALT", "").strip()
        static = env("FRONTEND_DIST", "").strip()
        return cls(
            database_url=env("DATABASE_URL", "").strip() or cls.database_url,
            cors_origins=_csv(env("CORS_ORIGINS")),
            trusted_proxy_hops=_parse_int(env("TRUSTED_PROXY_HOPS"), 0, "TRUSTED_PROXY_HOPS"),
            client_ip_headers=tuple(name.lower() for name in _csv(env("CLIENT_IP_HEADERS"))),
            max_concurrent_jobs=_parse_int(env("MAX_CONCURRENT_JOBS"), 1, "MAX_CONCURRENT_JOBS"),
            max_queued_jobs=_parse_int(env("MAX_QUEUED_JOBS"), 5, "MAX_QUEUED_JOBS"),
            job_timeout_seconds=_parse_int(env("JOB_TIMEOUT_SECONDS"), 600, "JOB_TIMEOUT_SECONDS"),
            result_cache_ttl_hours=_parse_int(
                env("RESULT_CACHE_TTL_HOURS"), 24, "RESULT_CACHE_TTL_HOURS"
            ),
            job_retention_days=_parse_int(env("JOB_RETENTION_DAYS"), 7, "JOB_RETENTION_DAYS"),
            max_topic_chars=_parse_int(env("MAX_TOPIC_CHARS"), 300, "MAX_TOPIC_CHARS"),
            max_instructions_chars=_parse_int(
                env("MAX_INSTRUCTIONS_CHARS"), 1000, "MAX_INSTRUCTIONS_CHARS"
            ),
            max_request_bytes=_parse_int(env("MAX_REQUEST_BYTES"), 16_384, "MAX_REQUEST_BYTES"),
            max_report_chars=_parse_int(env("MAX_REPORT_CHARS"), 60_000, "MAX_REPORT_CHARS"),
            jobs_per_ip_per_hour=_parse_int(env("JOBS_PER_IP_PER_HOUR"), 5, "JOBS_PER_IP_PER_HOUR"),
            jobs_per_ip_per_day=_parse_int(env("JOBS_PER_IP_PER_DAY"), 10, "JOBS_PER_IP_PER_DAY"),
            global_jobs_per_day=_parse_int(env("GLOBAL_JOBS_PER_DAY"), 100, "GLOBAL_JOBS_PER_DAY"),
            api_requests_per_ip_per_minute=_parse_int(
                env("API_REQUESTS_PER_IP_PER_MINUTE"), 300, "API_REQUESTS_PER_IP_PER_MINUTE"
            ),
            max_event_streams_per_ip=_parse_int(
                env("MAX_EVENT_STREAMS_PER_IP"), 4, "MAX_EVENT_STREAMS_PER_IP"
            ),
            ip_hash_salt=salt or secrets.token_hex(16),
            allowed_models=_csv(env("ALLOWED_MODELS")),
            enable_api_docs=_bool(env("ENABLE_API_DOCS"), True),
            static_dir=Path(static) if static else _default_static_dir(),
        )

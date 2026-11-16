"""Request and response schemas for the public HTTP API (``/api/v1``).

These models are the contract between the backend and the browser. They are
rendered into the OpenAPI document served at ``/api/docs``. Internal fields
(owner-token hashes, client IP hashes, raw exceptions) never appear here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Depth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class ReportStyle(str, Enum):
    TECHNICAL_REPORT = "technical_report"
    EXECUTIVE_BRIEF = "executive_brief"
    TUTORIAL = "tutorial"


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class ResearchCreate(BaseModel):
    """Body of ``POST /api/v1/research``.

    Length limits are enforced by the route using the server's configured
    limits (see ``GET /api/v1/meta``) so operators can tune them.
    """

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=3, description="The research topic or question.")
    instructions: str | None = Field(
        default=None, description="Optional extra guidance, e.g. audience or focus areas."
    )
    depth: Depth = Field(default=Depth.STANDARD, description="How much searching to do.")
    report_style: ReportStyle = Field(default=ReportStyle.TECHNICAL_REPORT)
    model: str | None = Field(
        default=None, description="Model id from `GET /api/v1/meta` `models`; default if omitted."
    )


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable, user-safe explanation.")
    request_id: str | None = None
    retry_after_seconds: int | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class StageOut(BaseModel):
    stage: str = Field(..., description="research | coding | synthesis")
    agent: str = Field(..., description="Display name of the agent running this stage.")
    status: StageStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 0
    searches: int = 0
    llm_calls: int = 0


class JobOptions(BaseModel):
    depth: Depth
    report_style: ReportStyle
    model: str
    instructions: str | None = None


class JobError(BaseModel):
    code: str
    message: str


class JobOut(BaseModel):
    """Public view of a research job."""

    id: str
    status: JobStatus
    topic: str
    options: JobOptions
    stages: list[StageOut]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    queue_position: int | None = Field(
        default=None, description="1-based position while queued; null otherwise."
    )
    error: JobError | None = None
    cached: bool = Field(default=False, description="True when served from a recent identical run.")
    result_available: bool = False


class JobCreated(JobOut):
    """Response to job creation. ``owner_token`` is returned exactly once."""

    owner_token: str | None = Field(
        default=None,
        description=(
            "Secret required to cancel this job (send as `X-Owner-Token`). "
            "Null when an existing job was returned."
        ),
    )


class SourceOut(BaseModel):
    title: str
    url: str
    snippet: str
    published: str | None = None
    provider: str
    query: str


class CitationCheckOut(BaseModel):
    matched: list[str] = Field(..., description="Report links found in retrieved search results.")
    unmatched: list[str] = Field(
        ..., description="Report links NOT found in search results; treat as unverified."
    )


class ResultOut(BaseModel):
    """Final output of a succeeded job."""

    job_id: str
    topic: str
    report_markdown: str = Field(..., description="The Manager Agent's report.")
    document_markdown: str = Field(
        ..., description="Report + retrieved sources + methodology (the download)."
    )
    research_notes: str = Field(..., description="Raw output of the Research Agent.")
    code_examples: str = Field(..., description="Raw output of the Coding Agent.")
    methodology_markdown: str
    sources: list[SourceOut]
    citation_check: CitationCheckOut
    search_queries: list[str]
    model: str
    provider: str
    duration_seconds: float
    token_usage: dict[str, Any]
    truncated: bool
    created_at: datetime


class JobDetail(JobOut):
    """A job plus its result (``null`` until the job has succeeded)."""

    result: ResultOut | None = None


class EventOut(BaseModel):
    id: int
    type: str
    stage: str | None = None
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class HealthOut(BaseModel):
    status: str
    version: str


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class ReadinessOut(BaseModel):
    status: str = Field(..., description="ready | degraded | unavailable")
    version: str
    checks: list[ReadinessCheck]


class LimitsOut(BaseModel):
    max_topic_chars: int
    max_instructions_chars: int
    jobs_per_ip_per_hour: int
    jobs_per_ip_per_day: int
    global_jobs_per_day: int
    job_timeout_seconds: int
    max_concurrent_jobs: int


class ModelOut(BaseModel):
    id: str
    provider: str
    default: bool


class MetaOut(BaseModel):
    version: str
    repository_url: str
    models: list[ModelOut]
    search_providers: list[str]
    depths: list[Depth]
    report_styles: list[ReportStyle]
    limits: LimitsOut
    persistence: str = Field(..., description="'persistent' or 'ephemeral' storage.")
    api_docs: bool = Field(..., description="Whether interactive docs are served at /api/docs.")


class UsageOut(BaseModel):
    """The caller's remaining quota (by client IP)."""

    jobs_today: int
    jobs_per_ip_per_day: int
    global_jobs_today: int
    global_jobs_per_day: int
    active_jobs: int
    max_concurrent_jobs: int
    queued_jobs: int
    max_queued_jobs: int

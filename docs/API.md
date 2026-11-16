# HTTP API

Interactive documentation (OpenAPI / Swagger UI) is served by the app at
**`/api/docs`** (ReDoc at `/api/redoc`, schema at `/api/openapi.json`). This
page summarises the contract; `src/research_team/web/schemas.py` is the
source of truth.

* Base path: `/api/v1` for resources; `/api/health*` for infrastructure.
* All responses are JSON except the event stream and downloads.
* Every response carries an `X-Request-ID` header (send your own to correlate).

## Endpoints

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/api/health` | Liveness | 200 |
| GET | `/api/health/ready` | Readiness: database, configuration, job runner, LLM provider, search | 200 (`ready`/`degraded`) or 503 |
| GET | `/api/v1/meta` | Models, depths, report styles, limits, persistence mode, version | 200 |
| GET | `/api/v1/usage` | The caller's quota usage (by client IP) | 200 |
| POST | `/api/v1/research` | Submit a research job | 202 new · 200 existing/cached |
| GET | `/api/v1/research/{id}` | Job + result (when succeeded) | 200 |
| GET | `/api/v1/research/{id}/status` | Lightweight status for polling | 200 |
| GET | `/api/v1/research/{id}/events` | Live progress (Server-Sent Events) | 200 stream |
| GET | `/api/v1/research/{id}/result` | Final result | 200 · 409 until succeeded |
| POST | `/api/v1/research/{id}/cancel` | Cancel (header `X-Owner-Token`) | 202 |
| GET | `/api/v1/research/{id}/download?format=md\|json` | Attachment download | 200 |

## Submitting a job

```bash
curl -s -X POST http://localhost:8000/api/v1/research \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 7d3c2a7e-6a4e-4a58-9d6b-1f0b8f1b2c3d' \
  -d '{
        "topic": "How to choose a vector database for RAG",
        "instructions": "Audience: backend engineers",
        "depth": "standard",
        "report_style": "technical_report",
        "model": "openai/gpt-oss-120b"
      }'
```

| Field | Type | Notes |
| --- | --- | --- |
| `topic` | string | 3 – `MAX_TOPIC_CHARS` (default 300) characters |
| `instructions` | string? | ≤ `MAX_INSTRUCTIONS_CHARS` (default 1000) |
| `depth` | `quick` \| `standard` \| `deep` | 2 / 4 / 6 web searches |
| `report_style` | `technical_report` \| `executive_brief` \| `tutorial` | Shape of the final report |
| `model` | string? | One of `GET /api/v1/meta` → `models[].id` |

Response (`202`): a job with `status: "queued"`, its `stages`, and an
`owner_token` that is returned **only once** — keep it to cancel the job.
A `200` returns an existing job instead: the same `Idempotency-Key` (24 h), an
identical request from you that is still active, or an identical request
answered recently (`cached: true`, consumes no quota).

## Job object

```json
{
  "id": "1f110bf132d11602591a555a38dd8cfa",
  "status": "running",
  "topic": "How to choose a vector database for RAG",
  "options": {"depth": "standard", "report_style": "technical_report", "model": "openai/gpt-oss-120b", "instructions": null},
  "stages": [
    {"stage": "research", "agent": "Research Agent", "status": "completed", "started_at": "…", "finished_at": "…", "attempts": 1, "searches": 2, "llm_calls": 3},
    {"stage": "coding", "agent": "Coding Agent", "status": "running", "started_at": "…", "finished_at": null, "attempts": 1, "searches": 0, "llm_calls": 1},
    {"stage": "synthesis", "agent": "Manager Agent", "status": "pending", "started_at": null, "finished_at": null, "attempts": 0, "searches": 0, "llm_calls": 0}
  ],
  "created_at": "…", "started_at": "…", "finished_at": null,
  "queue_position": null, "error": null, "cached": false, "result_available": false
}
```

Job `status`: `queued → running → succeeded | failed | cancelled`.
Stage `status`: `pending | running | completed | failed | cancelled`.
`attempts > 1` means the stage was re-run on a fallback provider.

## Live progress (SSE)

```bash
curl -N http://localhost:8000/api/v1/research/$ID/events
```

```text
retry: 3000

id: 5
data: {"id":5,"type":"search","stage":"research","message":"Searched: vector database benchmarks","data":{"query":"vector database benchmarks","results":5,"ok":true},"timestamp":"…"}

event: end
data: {"status": "succeeded"}
```

* Each event is a default `message` event whose JSON matches `EventOut`.
* Event `type`s: `queued`, `run_started`, `stage_started`, `stage_completed`,
  `stage_failed`, `llm_call`, `search`, `retry`, `provider_fallback`,
  `run_completed`, `run_failed`, `run_cancelled`.
* Resume with `Last-Event-ID` (browsers do this automatically) or `?after=<id>`.
* The stream ends with a named `end` event once the job is terminal; a comment
  heartbeat is sent every 15 s.
* Every event reflects a real engine state transition — nothing is simulated.

## Result object (`GET …/result`)

`report_markdown` (the Manager Agent's report), `document_markdown` (report +
retrieved sources + methodology — the download), `research_notes`,
`code_examples`, `methodology_markdown`, `sources[]` (`title`, `url`,
`snippet`, `published`, `provider`, `query`), `citation_check`
(`matched[]` — links found in retrieved search results; `unmatched[]` — links
**not** found, treat as unverified), `search_queries[]`, `model`, `provider`,
`duration_seconds`, `token_usage`, `truncated`, `created_at`.

## Errors

All errors share one envelope:

```json
{"error": {"code": "daily_limit", "message": "You have reached the daily limit …", "request_id": "9f2c…", "retry_after_seconds": 86400}}
```

| HTTP | `code` | Meaning |
| --- | --- | --- |
| 403 | `forbidden` | Missing/invalid `X-Owner-Token` on cancel |
| 404 | `not_found` | Unknown job (or expired and deleted) |
| 409 | `not_ready`, `already_finished` | Result not available yet · job already terminal |
| 413 | `payload_too_large` | Body exceeds `MAX_REQUEST_BYTES` |
| 422 | `invalid_request`, `invalid_topic`, `topic_too_long`, `instructions_too_long`, `invalid_model`, `invalid_idempotency_key` | Validation |
| 429 | `too_many_requests`, `hourly_limit`, `daily_limit`, `global_daily_limit`, `too_many_streams` | Limits (`Retry-After` header set) |
| 503 | `server_busy`, `not_configured` | Queue full · engine not configured |
| 500 | `internal_error` | Unexpected error (details only in server logs) |

Failed jobs carry `error.code` ∈ `rate_limited`, `provider_unavailable`,
`timeout`, `cancelled`, `interrupted`, `configuration`, `workflow_error`,
`internal_error`, with a user-safe `message`.

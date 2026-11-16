# Implementation Plan and Architecture Decisions

This document records how version 2.0 turned the Multi-Agent Research Team CLI
into a public web platform: the audit findings, the decisions taken (and why),
and how each requirement was verified. It is a record of work done, written
for maintainers and reviewers.

## Phase 1 — Repository audit (baseline)

| Item | Finding |
| --- | --- |
| Code | ~600 lines across `cli`, `crew`, `agents`, `tasks`, `config`, `compat`, `exceptions`, `logging_config` |
| Tests | 39 passed with CrewAI installed (34 passed + 2 skipped modules without it) |
| Lint / types | Ruff clean; mypy clean |
| CI | Lint, format, mypy, pytest on Python 3.10–3.12 |

Defects found (the first five were known; the rest surfaced while verifying
against live services):

1. `LOG_LEVEL` was parsed but never applied.
2. Retries wrapped `crew.kickoff()`, so one failed request re-ran the whole pipeline.
3. `os.environ.setdefault` meant keys in an `AppConfig` could be silently ignored.
4. Errors (and logs) were written to stdout, mixing with the report.
5. The version was duplicated in `pyproject.toml` and `__init__.py`.
6. **The default model no longer existed:** Groq retired `llama-3.3-70b-versatile`
   (live API: `model_not_found`), so the 1.x CLI could not complete a run.
7. CrewAI's global console formatter printed emoji panels to stdout outside a
   `Crew`, crashing on Windows' cp1252 console.
8. CrewAI re-runs a whole agent task after an error (`max_retry_limit=2`) and
   re-invokes the LLM through fallback paths, multiplying requests to a
   rate-limited provider.
9. A 2,048-token budget truncated the final report before its References section.
10. The research agent sometimes omitted URLs, leaving the manager nothing to cite.

## Phase 2 — Decisions

| # | Decision | Alternatives considered | Reason |
| --- | --- | --- | --- |
| D1 | **One container** serving FastAPI + the built React SPA | Separate frontend host + API host; microservices | Simplest deployable unit on a free tier; same-origin (no CORS); one URL. Split hosting remains possible. |
| D2 | **Render Free** as the reference host | Hugging Face Spaces, Fly.io, Railway, Koyeb, Cloud Run | HF Docker Spaces now need PRO (official docs). Render Free is Docker-capable, needs no card for Free instances, and suspends instead of billing. Constraints (512 MB, spin-down, ephemeral disk) drove D4–D6. |
| D3 | **Staged pipeline** (each task executed separately) instead of `crew.kickoff()` | Keep kickoff + outer retry | Enables per-call retries, per-stage provider fallback, real progress events, cancellation between steps. |
| D4 | **Per-call retries** in a `CallGuard` (backoff + jitter + `Retry-After`), agents set to `max_retry_limit=0`, guard "trips" after a terminal error | LiteLLM `num_retries`; CrewAI retries | Only the failed request is retried; nothing else re-runs; CrewAI's internal re-invocations cannot hammer an exhausted provider. |
| D5 | **Jobs persisted before execution**, bounded thread pool, restart recovery | Celery/RQ + Redis; FastAPI `BackgroundTasks` | No extra service to host; survives restarts with a persistent DB; `BackgroundTasks` is in-memory only. A separate worker is the documented upgrade path. |
| D6 | **SQLite by default, Postgres via `DATABASE_URL`** (Neon Free recommended), SQLAlchemy 2 + Alembic | Postgres-only; Redis | Zero-setup locally; durable free option in production; migrations from day one. `pg8000` (BSD) instead of LGPL psycopg. |
| D7 | **SSE** for live progress (events stored in the DB, streamed by polling) | WebSockets; in-memory pub/sub | One-way stream suffices; works through proxies; resumable with `Last-Event-ID`; correct across restarts. |
| D8 | **Own search tool** (Serper → Tavily fallback) replacing `crewai_tools.SerperDevTool` | Keep crewai-tools | Records every real source, enforces a search budget, frames results as untrusted data, no arbitrary URL fetching (SSRF), drops a heavy dependency. |
| D9 | **Provider abstraction over LiteLLM** (`is_litellm=True` for all) | CrewAI native SDK providers | One code path for Groq/Gemini/OpenRouter/OpenAI-compatible/Ollama without extra SDKs; explicit credentials. |
| D10 | **Citation check + factual methodology** generated from engine data | Trust model output | The system must not claim verification it did not do. |
| D11 | **Capability URLs + owner token** for jobs; no user accounts | OAuth / email login | No paid auth service; anonymous use with quotas; sharing a result is sharing a link. |
| D12 | **Default model `openai/gpt-oss-120b`**, `reasoning_effort=low`, larger output budget for synthesis | Smaller model | Strongest model Groq serves; budgets tuned to the measured 8K TPM free limit. |

## Phase 3–5 — Implementation summary

* **Engine** (`src/research_team/`): `providers.py` (provider registry,
  `CallGuard`, guarded LLM), `search.py` (providers, source collector, tool),
  `report.py` (citation check, code syntax check, methodology), `progress.py`
  (events, `RunControl`), staged `crew.py`; hardened prompts in `tasks.py`.
* **Web** (`src/research_team/web/`): settings, models + Alembic migration,
  repository, job manager, rate limiting, ASGI security middleware, health
  probes, routes, app factory, `research-team-web` server.
* **Frontend** (`frontend/`): React + TypeScript SPA — landing, workspace with
  live agent monitoring, results, history, about; built into `frontend/dist`
  and served by the API.

## Phase 6 — Verification

| Requirement | How it was verified |
| --- | --- |
| Original CLI works | Real run against Groq + Serper (2026-11-15): 3 agents, 2 searches, 9 sources, ~10K tokens, 13 s; stdout contains only the report |
| Real AI research through the API | Real jobs via HTTP: live SSE events, stage counters, real 429s absorbed by per-call retries, report with all sections, 5/5 citations matched to retrieved sources |
| Retry granularity | Integration test drives real CrewAI agents with scripted LiteLLM responses: one provider request per failure, fallback re-runs only the current stage |
| Job lifecycle, cancellation, quotas, recovery | Backend test suite (API → runner → persistence → SSE → downloads) |
| Frontend journey | Playwright E2E against the real API with a deterministic test engine |
| Security headers, limits, CORS, IP handling | Backend tests |
| Real UI with the real engine | Playwright drove the built site against the real server: live agent status, full report, 5/5 citations matched, zero console errors; real mid-run cancellation verified via the API |
| PostgreSQL (Neon path) | `tests/test_postgres.py` runs migrations, repository and the API lifecycle on a Postgres service container in CI (no Postgres on the development machine) |
| Docker image | Built and smoke-tested in CI (Docker is not available on the development machine) |
| Public deployment | Requires the owner's Render account and keys — prepared, not performed (see DEPLOYMENT.md) |

## Phase 7+ — Remaining work for the owner

1. Create the Render service from `render.yaml` and add the API keys.
2. Optionally create a Neon database and set `DATABASE_URL`.
3. Verify the live site with the checklist in DEPLOYMENT.md, including the
   client-IP check, then add the URL to the README.

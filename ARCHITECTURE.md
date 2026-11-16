# Architecture (High-Level Design)

This document describes the high-level design of the Multi-Agent Research Team
platform: its components, runtime flow, key design decisions, and extension
points. Decision rationale is recorded in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## 1. System context

```mermaid
flowchart LR
    visitor([Visitor's browser]) -->|HTTPS| app
    operator([Operator / script]) -->|CLI| cli[CLI]
    subgraph app[Docker container]
        web[React website]
        api[FastAPI /api]
        runner[Job runner]
    end
    api --> runner
    cli --> engine
    runner --> engine[Research engine]
    engine -->|chat completions| llm[(Groq · Gemini · OpenRouter · Ollama)]
    engine -->|web search| search[(Serper · Tavily)]
    runner --> db[(SQLite or Postgres)]
```

The **research engine** is a reusable Python library. The **CLI** and the **web
app** are two thin interfaces over the same entry point,
`run_research_workflow(topic, config, options, on_progress=..., control=...)`,
which returns a structured `ResearchResult`.

## 2. Component view

```mermaid
flowchart TD
    subgraph Interfaces
        cli[cli.py]
        subgraph web[web/]
            app[app.py · routes.py · middleware.py]
            jobs[jobs.py · repository.py]
            dbm[db.py · models.py · migrations/]
        end
    end
    subgraph Engine
        crew[crew.py<br/><i>staged pipeline</i>]
        agents[agents.py]
        tasks[tasks.py<br/><i>hardened prompts</i>]
        providers[providers.py<br/><i>LLM registry · CallGuard</i>]
        search[search.py<br/><i>Serper/Tavily · sources</i>]
        report[report.py<br/><i>citation & code checks</i>]
    end
    subgraph Platform
        config[config.py]
        progress[progress.py<br/><i>events · RunControl</i>]
        exceptions[exceptions.py]
        compat[compat.py]
        logging[logging_config.py]
    end
    cli --> crew
    app --> jobs --> crew
    jobs --> dbm
    crew --> agents & tasks & providers & search & report
    providers --> config & compat & progress
    crew --> progress
```

Dependency direction is strict: interfaces → engine → platform. The engine
never imports the web layer.

| Module | Responsibility |
| --- | --- |
| `crew.py` | Runs research → coding → synthesis as separate stages; provider fallback per stage; assembles `ResearchResult`. |
| `providers.py` | Provider registry (all via LiteLLM, explicit credentials); `CallGuard` retries one request with backoff + jitter, honours `Retry-After`, checks cancellation. |
| `search.py` | Search providers with fallback; untrusted-data framing; search budget; `SourceCollector` of every retrieved result. |
| `report.py` | Citation-marker normalisation, link-vs-source check, Python syntax check, size limit, methodology and sources sections. |
| `progress.py` | `ProgressEvent` types and `RunControl` (cancellation + deadline). |
| `tasks.py` / `agents.py` | Prompts with delimited user data; agents without delegation, code execution, or task-level retries. |
| `web/jobs.py` | Persist-then-execute job runner, bounded thread pool, restart recovery, cancellation, janitor. |
| `web/routes.py` | REST + SSE endpoints, validation, quotas, caching, idempotency. |
| `web/middleware.py` | Request IDs, security headers/CSP, body limit, per-IP rate limit (pure ASGI). |

## 3. Runtime flow of one research job

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API
    participant D as Database
    participant W as Worker thread
    participant E as Engine
    participant P as LLM / Search

    B->>A: POST /api/v1/research
    A->>D: validate, quotas, dedup/cache, insert job (queued)
    A-->>B: 202 {id, owner_token}
    B->>A: GET /research/{id}/events (SSE)
    A->>W: submit(id)
    W->>D: queued → running
    W->>E: run_research_workflow(...)
    loop each stage: research, coding, synthesis
        E->>D: stage_started (via observer)
        E->>P: model requests / searches (CallGuard: retry only the failed call)
        E->>D: search, llm_call, retry … events
        E->>D: stage_completed
    end
    E-->>W: ResearchResult
    W->>D: save result, running → succeeded
    A-->>B: events streamed as they are stored, then "end"
    B->>A: GET /research/{id} (report, sources, citation check)
```

**Failure handling.** A transient error retries one request. If a provider stays
rate-limited or unavailable, the current stage restarts on the next configured
fallback provider; completed stages are never repeated. Cancellation and the
time budget are checked before every model request and search.

## 4. Key data structures

```mermaid
classDiagram
    class ResearchJob {
        id (128-bit random)
        status: queued|running|succeeded|failed|cancelled
        topic, instructions, depth, report_style, model
        stages: per-stage status, timestamps, counters
        cache_key, owner_token_hash, client_hash
        error_code, error_message, expires_at
    }
    class JobEvent {
        id, job_id, type, stage, message, data, created_at
    }
    class ResearchResultRow {
        job_id, payload (ResultOut)
    }
    ResearchJob "1" --> "*" JobEvent
    ResearchJob "1" --> "0..1" ResearchResultRow
```

`AppConfig` (engine) and `WebSettings` (server) are frozen, validated
dataclasses built from environment variables.

## 5. Cross-cutting concerns

* **Resilience** — per-call retries, per-stage provider fallback, bounded
  queues, timeouts, restart recovery, graceful shutdown (running jobs recorded
  as `interrupted`).
* **Security & abuse protection** — see [SECURITY.md](SECURITY.md).
* **Observability** — structured logs under the `research_team` logger
  namespace (stderr), request ids, readiness checks that probe the LLM provider
  cheaply (model list) and confirm the configured model is still served.
* **Performance** — heavy imports are lazy; CrewAI runs in worker threads, never
  on the event loop; the SSE endpoint is async and polls the database once per
  second; finished jobs expire.
* **Privacy** — salted IP hashes only; telemetry disabled.

## 6. Extensibility

* **Another LLM provider** — add it to `providers.provider_spec` (anything
  LiteLLM supports).
* **Another search provider** — implement `SearchProvider.search()` in `search.py`.
* **Another agent/stage** — add a factory in `agents.py`/`tasks.py`, a `Stage`
  member in `progress.py`, and a call in `ResearchPipeline.run`; the UI picks up
  stages from the API.
* **Scale out** — move `JobManager._execute` into a separate worker process that
  polls `queued` jobs (the database already holds all state), then run several
  API instances behind a load balancer (move the in-memory API rate limiter to a
  shared store at that point).

## 7. Known constraints

* **Free-tier quotas** bound throughput (Groq: 8K tokens/minute per model);
  see [FREE_TIER_INFRASTRUCTURE.md](FREE_TIER_INFRASTRUCTURE.md).
* **Single instance.** The API rate limiter and concurrency caps are in-memory;
  job quotas are in the database.
* **Sequential by design.** Stages run in order so each can build on the
  previous one; parallel stages are a possible future mode.

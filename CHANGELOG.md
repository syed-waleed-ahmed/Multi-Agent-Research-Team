# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.1] - 2026-11-16

First verified public deployment: https://multi-agent-research-team-aasz.onrender.com (Render Free + Neon Free).
Every fix below was found by exercising that deployment.

### Fixed

- Per-visitor quotas behind Render/Cloudflare: clients are identified by
  `CF-Connecting-IP` (`CLIENT_IP_HEADERS`) instead of a changing proxy hop.
- Zero-downtime deploys no longer interrupt research runs: workers heartbeat
  their jobs (migration `0002`), recovery only fails jobs with a stale
  heartbeat, a periodic sweep picks up unclaimed queued jobs, and shutdown
  drains running jobs (`SHUTDOWN_DRAIN_SECONDS`, after closing open
  connections within `GRACEFUL_SHUTDOWN_SECONDS`; both fit Render Free's fixed
  30 s shutdown window).
- Rate limits are retried against a time budget (`RATE_LIMIT_MAX_WAIT_SECONDS`)
  using the provider's own retry hint (header or message) instead of three
  short retries that could not outlast a token-per-minute window.
- An interrupted job no longer shows a stage as still running.
- The citation check ignores local and private addresses (for example a
  `http://localhost:16686` dashboard link in setup instructions); they are
  never citations.

### Added

- `LLM_FALLBACK_PROVIDERS` accepts `provider:model` entries (e.g.
  `groq:openai/gpt-oss-20b`), a free fallback because free-tier token limits
  are per model.

## [2.0.0] - 2026-11-15

The CLI becomes a public, open-source web research platform. The CLI remains a
supported interface.

### Added

- **Web application** (`research-team-web`): FastAPI backend and a React +
  TypeScript website (landing page, research workspace, live agent monitoring,
  results with sources and citation check, history, about/docs), served from
  one container.
- **REST API** under `/api/v1` with OpenAPI docs at `/api/docs`; liveness and
  readiness probes at `/api/health` and `/api/health/ready`.
- **Live progress** over Server-Sent Events, backed by real engine events
  (stage started/completed/failed, searches, model requests, retries, provider
  fallbacks). Resumable with `Last-Event-ID`.
- **Background jobs** persisted in SQLite or PostgreSQL (SQLAlchemy 2 +
  Alembic migrations), a bounded worker pool, restart recovery, cooperative
  cancellation with owner tokens, expiry cleanup.
- **Abuse protection** for shared free quotas: per-IP hourly/daily and global
  daily job limits, API request rate limiting, concurrent-stream caps, queue
  limits, request size limits, result caching and idempotency keys.
- **Security hardening**: CSP and security headers, request IDs, safe error
  envelopes, CORS allowlist, salted IP hashing, prompt-injection framing of
  user input and web content, no arbitrary outbound requests.
- **Provider abstraction**: Groq (default), Gemini, OpenRouter, any
  OpenAI-compatible endpoint, and Ollama, with per-stage fallback
  (`LLM_PROVIDER`, `LLM_FALLBACK_PROVIDERS`).
- **Search abstraction**: Serper with Tavily fallback, a per-run search budget,
  and a record of every retrieved source.
- **Report quality checks**: links are compared with the URLs actually
  retrieved (unmatched links are flagged), Python code blocks are syntax-checked
  (never executed), and a factual methodology section is generated from engine
  data. Downloads include the retrieved sources and methodology.
- Research options: depth (`quick`/`standard`/`deep`), report style
  (`technical_report`/`executive_brief`/`tutorial`), extra instructions, model
  selection. New CLI flags: `--depth`, `--style`, `--instructions`, `--provider`,
  `--workflow-timeout`.
- Deployment: multi-stage `Dockerfile`, Render Free blueprint (`render.yaml`),
  `DEPLOYMENT.md`, `FREE_TIER_INFRASTRUCTURE.md`, `IMPLEMENTATION_PLAN.md`,
  `docs/API.md`, security constraints for transitive dependencies.
- CI: frontend lint/type-check/unit tests/build, Playwright end-to-end tests,
  `pip-audit` and `npm audit`, Docker image build and smoke test.

### Changed

- **Default model is now `openai/gpt-oss-120b`.** Groq retired
  `llama-3.3-70b-versatile`, which made 1.x runs fail with `model_not_found`.
  If your `.env` still sets `GROQ_MODEL=llama-3.3-70b-versatile`, update it.
- The pipeline executes each stage separately instead of `crew.kickoff()`;
  `build_crew()` was removed (it was not part of the public API).
- Retries now apply to a single failed model request (exponential backoff with
  jitter, honouring `Retry-After`); a provider that stays unavailable triggers a
  fallback for the current stage only. Completed work is never repeated.
- `GROQ_MAX_TOKENS` default raised to 2048; the final report has its own budget
  (`SYNTHESIS_MAX_TOKENS`, default 3072). `REASONING_EFFORT=low` for reasoning
  models keeps runs inside free-tier token limits.
- `--output` now saves the full document (report + retrieved sources + methodology).
- `ResearchResult` gained fields (sources, citation check, notes, code,
  methodology, document, provider); the original fields are unchanged.
- Report sections: Executive Summary, Key Findings, Recommended Approach,
  Technical Implementation Notes, Risks/Open Questions, References (style-dependent).
- Packaging: the version is single-sourced from `research_team.__version__`;
  SPDX license metadata; web dependencies in the `[web]` extra.

### Removed

- `crewai-tools` and `groq` dependencies (replaced by the built-in search tool;
  LiteLLM talks to Groq directly).

### Fixed

- `LOG_LEVEL` from the environment or `.env` is now applied (precedence:
  `--log-level`, `--verbose`, `LOG_LEVEL`, `INFO`).
- Credentials in an `AppConfig` are passed explicitly to clients and are no
  longer overridden by (or written into) environment variables.
- Errors and logs go to stderr; stdout carries only the report.
- CrewAI's console panels no longer leak to stdout (and no longer crash
  non-UTF-8 Windows consoles); CLI output streams are UTF-8 safe.
- gpt-oss citation markers (`【n†url】`) are converted to Markdown links.

## [1.0.0] - 2026-07-05

First production-ready release.

### Added

- Structured, validated configuration (`AppConfig`) with per-invocation CLI
  overrides for the model, temperature, token budget, rate limit, retries, and
  timeout.
- Typed exception hierarchy (`ConfigError`, `DependencyError`, `WorkflowError`,
  `RateLimitExceededError`) mapped to conventional process exit codes.
- Exponential-backoff retries on transient and rate-limit provider errors.
- Structured workflow result (`ResearchResult`) exposing the report, model,
  duration, and token usage.
- Structured logging with `--verbose`, `--quiet`, and `--log-level` controls.
- Full test suite plus `ruff`, `mypy`, and `pytest` configuration and a CI
  workflow.
- Shipped type information via a `py.typed` marker (PEP 561).
- `ARCHITECTURE.md`, `CONTRIBUTING.md`, a `Makefile`, and an MIT `LICENSE`.
- Community-health documents: `SECURITY.md`, `CODE_OF_CONDUCT.md`, a pull-request
  template, and bug-report/feature-request issue templates.

### Changed

- Restructured the package into a `src/` layout under `research_team`, replacing
  the previous `src` import package.
- Heavy dependencies (CrewAI, LiteLLM) are now imported lazily for fast CLI
  startup and a hermetic, network-free test suite.
- CrewAI telemetry and interactive tracing are disabled by default.
- Pinned `crewai` and `crewai-tools` to the tested `>=1.15,<2.0` range.

### Fixed

- Groq requests failed with `property 'cache_breakpoint' is unsupported` because
  CrewAI's LiteLLM code path did not strip its internal cache-breakpoint marker.
  A guarded, idempotent compatibility shim now removes the marker before the
  request is sent.
- `.gitignore` no longer excludes the committed `.env.example` template.
- Configured mypy to skip third-party stubs (for example numpy's PEP 695 `type`
  statements) so CI type-checking passes across the Python 3.10-3.12 matrix.

[Unreleased]: https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/syed-waleed-ahmed/Multi-Agent-Research-Team/releases/tag/v1.0.0

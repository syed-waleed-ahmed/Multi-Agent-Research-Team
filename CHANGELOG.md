# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

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

### Changed

- Restructured the package into a `src/` layout under `research_team`, replacing
  the previous `src` import package.
- Heavy dependencies (CrewAI, LiteLLM) are now imported lazily for fast CLI
  startup and a hermetic, network-free test suite.
- Default model is now `llama-3.3-70b-versatile`, which reliably completes the
  three-agent workflow within Groq's free-tier token limits.
- CrewAI telemetry and interactive tracing are disabled by default.
- Pinned `crewai` and `crewai-tools` to the tested `>=1.15,<2.0` range.

### Fixed

- Groq requests failed with `property 'cache_breakpoint' is unsupported` because
  CrewAI's LiteLLM code path did not strip its internal cache-breakpoint marker.
  A guarded, idempotent compatibility shim now removes the marker before the
  request is sent.
- `.gitignore` no longer excludes the committed `.env.example` template.

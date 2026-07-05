# Multi-Agent Research Team

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Style: ruff](https://img.shields.io/badge/style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Typed: mypy](https://img.shields.io/badge/typed-mypy-2A6DB2.svg)](https://mypy-lang.org/)

A production-oriented command-line application that coordinates a team of
specialized AI agents (Research, Coding/Analysis, and a synthesizing Manager)
to research any topic and produce a professional Markdown report.

It is built with [CrewAI](https://github.com/crewAIInc/crewAI),
[Groq](https://console.groq.com/), and [Serper](https://serper.dev/), and is
organized as a clean, layered application that can grow from a CLI into a web
service or background job runner.

```bash
multi-agent-research-team --topic "Applications of multi-agent systems in AI automation"
```

## Table of contents

- [Highlights](#highlights)
- [Architecture at a glance](#architecture-at-a-glance)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output](#output)
- [Development](#development)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Extending the system](#extending-the-system)
- [License](#license)

## Highlights

- **Deterministic multi-agent pipeline.** A sequential Research, Coding, and
  Manager workflow with explicit task context, so runs are reproducible and
  easy to debug.
- **Production resilience.** Typed exceptions, exponential-backoff retries on
  transient and rate-limit errors, and conventional process exit codes.
- **Fast, testable core.** Heavy dependencies are imported lazily, so the CLI
  starts instantly and the logic is unit-tested without network access.
- **Structured configuration.** Immutable, validated settings loaded from
  environment variables and overridable per invocation via CLI flags.
- **Observability and privacy.** Structured logging with adjustable verbosity;
  third-party telemetry is disabled by default.
- **Clean packaging.** A `src/` layout, a console entry point, shipped type
  information (PEP 561), and a `ruff` + `mypy` + `pytest` toolchain with CI.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full high-level design, component
diagrams, and extension points.

## Architecture at a glance

```text
CLI  ->  Workflow (orchestration)  ->  Agents / Tasks  ->  Config (LLM + tools)
                                                           Exceptions, Logging, Compat
```

The dependency direction is strict (top to bottom). The workflow exposes a
single transport-agnostic entry point, `run_research_workflow(topic, config)`,
which returns a structured `ResearchResult`. That function can be wrapped by a
CLI, an HTTP API, or a background job without any change to the domain layer.

## Requirements

- Python 3.10 or newer
- A [Groq](https://console.groq.com/) API key
- A [Serper](https://serper.dev/) API key

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .
```

To install the development tooling (tests, linter, type checker):

```bash
pip install -e ".[dev]"
```

## Configuration

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | yes | | Groq API key. |
| `SERPER_API_KEY` | yes | | Serper search API key. |
| `GROQ_MODEL` | no | `llama-3.3-70b-versatile` | Groq model id. |
| `GROQ_TEMPERATURE` | no | `0.2` | Sampling temperature (0.0 to 2.0). |
| `GROQ_MAX_TOKENS` | no | `1024` | Maximum tokens per response. |
| `GROQ_MAX_RETRIES` | no | `3` | Retries on transient provider errors. |
| `MAX_RPM` | no | | Cap requests-per-minute across the crew. |
| `REQUEST_TIMEOUT` | no | | Per-agent execution timeout in seconds. |
| `LOG_LEVEL` | no | `INFO` | Logging level. |

The default model balances quality with Groq's free-tier token limits. For
faster, cheaper runs, set `GROQ_MODEL=llama-3.1-8b-instant`.

## Usage

Run the workflow:

```bash
multi-agent-research-team --topic "Using CrewAI for multi-agent research"
```

Save the report to a file:

```bash
multi-agent-research-team --topic "Vector databases for RAG" --output reports/rag.md
```

Override model settings for a single run:

```bash
multi-agent-research-team --topic "Async Python patterns" \
  --model llama-3.1-8b-instant --temperature 0.4 --max-tokens 1500
```

You can also run it as a module: `python -m research_team --topic "..."`.

### Command-line options

| Flag | Description |
| --- | --- |
| `--topic` | Required. Research topic or user goal. |
| `-o, --output` | Save the final Markdown report to a file. |
| `--model` | Override the Groq model id. |
| `--temperature` | Override the sampling temperature. |
| `--max-tokens` | Override the maximum tokens per response. |
| `--max-rpm` | Cap requests-per-minute across the crew. |
| `--max-retries` | Retries on transient provider errors. |
| `--timeout` | Per-agent execution timeout in seconds. |
| `-v, --verbose` | Verbose agent and crew tracing plus DEBUG logs. |
| `-q, --quiet` | Print only the report (machine-friendly). |
| `--log-level` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `--version` | Print the version and exit. |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Workflow failure (including rate limiting) |
| `2` | Configuration error (missing or invalid settings) |
| `3` | Missing dependency |
| `130` | Interrupted (Ctrl-C) |

## Output

The application produces a structured Markdown report with sections for the
problem restatement, key findings, a recommended approach, technical
implementation notes, and references. The report is printed to the terminal and,
optionally, saved to a file.

## Development

```bash
pip install -e ".[dev]"

pytest              # run the test suite
ruff check .        # lint
ruff format .       # format
mypy                # type-check
```

Common tasks are also available through the Makefile (`make check` runs every
quality gate). The test suite runs without network access or API keys: the
CrewAI-heavy paths are mocked, and the few tests that construct real CrewAI
objects make no API calls.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and
[CHANGELOG.md](CHANGELOG.md) for the release history.

## Project structure

```text
multi-agent-research-team/
├── ARCHITECTURE.md          # High-level design (HLD)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── pyproject.toml           # Packaging and tooling configuration
├── requirements.txt
├── .env.example
├── src/
│   └── research_team/
│       ├── __init__.py      # Public API (lazy)
│       ├── __main__.py      # python -m research_team
│       ├── cli.py           # Command-line interface
│       ├── crew.py          # Orchestration and resilience
│       ├── agents.py        # Agent factories
│       ├── tasks.py         # Task factories and context wiring
│       ├── config.py        # Configuration and LLM/tool factories
│       ├── exceptions.py    # Typed error hierarchy
│       ├── logging_config.py
│       └── compat.py        # Third-party compatibility shims
└── tests/
```

## Troubleshooting

- **`rate-limited ... after N retries`.** Groq's free tier enforces a
  per-minute token budget that the three-agent workflow can exceed on large
  topics. Wait a minute, use a higher-tier key, lower `GROQ_MAX_TOKENS`, or try
  `--model llama-3.1-8b-instant`.
- **`Missing required environment variables`.** Ensure `.env` exists (copied
  from `.env.example`) and that both API keys are set.

## Extending the system

The architecture is intentionally small but layered, so it can grow into:

- A FastAPI service layer around `run_research_workflow`.
- Background job execution and result persistence.
- Caching for repeated research runs.
- Additional agents and tasks, or a parallel/hierarchical process.

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## License

Released under the [MIT License](LICENSE).

Created by Syed Waleed Ahmed.

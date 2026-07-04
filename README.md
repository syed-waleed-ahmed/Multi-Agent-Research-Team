# Multi-Agent Research Team

Multi-Agent Research Team is a production-oriented command-line application built with CrewAI, Groq, and Serper. It coordinates three specialized agents to research a topic, generate implementation-oriented notes, and synthesize a final professional report.

## Overview

The project is designed as a standalone research workflow that can be run from the terminal, automated in scripts, or extended into a larger system. It follows a deterministic execution path so results are easier to reason about and debug in production environments.

## Capabilities

- Web-backed research with the Serper search tool.
- Structured technical synthesis from a manager agent.
- Code-oriented output for practical implementation guidance.
- Optional Markdown export for reports or downstream publishing.
- Environment-driven configuration for model selection and token limits.

## Architecture

1. [src/main.py](src/main.py) provides the CLI entry point.
2. [src/config.py](src/config.py) loads and validates runtime configuration.
3. [src/agents.py](src/agents.py) defines the specialist agents.
4. [src/tasks.py](src/tasks.py) defines the task prompts and expected outputs.
5. [src/crew.py](src/crew.py) orchestrates the sequential workflow.

The codebase is intentionally lightweight, but the structure supports evolution toward a broader production architecture, such as a web API, a background job runner, or a multi-tenant research service.

## Requirements

- Python 3.10 or newer.
- A Groq API key.
- A Serper API key.

## Configuration

Copy [.env.example](.env.example) to `.env` and populate the required values.

Environment variables:

- `GROQ_API_KEY` - required.
- `SERPER_API_KEY` - required.
- `GROQ_MODEL` - optional, defaults to `llama-3.1-8b-instant`.
- `GROQ_TEMPERATURE` - optional, defaults to `0.2`.
- `GROQ_MAX_TOKENS` - optional, defaults to `1024`.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Or install the package in editable mode:

```bash
pip install -e .
```

## Usage

Run the workflow from the project root:

```bash
python -m src --topic "Applications of multi-agent systems in AI automation workflows"
```

Save the generated report to disk:

```bash
python -m src --topic "Applications of multi-agent systems in AI automation workflows" --output reports/research.md
```

## Output

The application prints a Markdown report to the terminal and can also persist that report to a file. The report is structured for technical readers and includes research findings, implementation guidance, and references.

## Project Structure

```text
multi-agent-research-team/
├── .env.example
├── requirements.txt
└── src/
	├── __init__.py
	├── __main__.py
	├── agents.py
	├── config.py
	├── crew.py
	├── main.py
	└── tasks.py
```

## Professional Notes

- Startup is lazy and user-facing help works without loading the full agent stack.
- Missing dependencies and missing environment variables are reported with clear error messages.
- Output directories are created automatically when saving reports.
- The workflow is sequential to keep runtime behavior predictable.

## Extending the System

The current codebase can be extended into a fuller production system by adding:

- A FastAPI service layer.
- Background job execution and persistence.
- Structured logging and tracing.
- Caching for repeated research runs.
- A front-end dashboard or internal portal.

## Author

Created by Syed Waleed Ahmed
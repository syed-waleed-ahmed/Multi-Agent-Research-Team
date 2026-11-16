---
name: Bug report
about: Report a problem with the CLI, the web app or the API
title: "[Bug] "
labels: bug
assignees: ""
---

## Description

A clear and concise description of the bug.

## Where it happens

- [ ] CLI (`multi-agent-research-team`)
- [ ] Web app (browser)
- [ ] REST API (`/api/v1`)
- [ ] Docker image / deployment (e.g. Render)

## Steps to reproduce

1. Command run (for example: `multi-agent-research-team --topic "..." --depth quick`)
   or the steps taken in the web app / the API request sent
2. ...

## Expected behavior

What you expected to happen.

## Actual behavior

What actually happened. Please include:

- CLI: the relevant log output (run with `--verbose`) and the process exit code.
- Web app / API: the error message and the **request id** shown in the error,
  plus any browser console errors.

Redact any API keys, secrets or database URLs.

## Environment

- Version (`multi-agent-research-team --version`, or the version in the web app footer):
- OS:
- Python version (`python --version`):
- Browser and version (web app only):
- LLM provider and model (e.g. Groq `openai/gpt-oss-120b`):
- Database (SQLite / PostgreSQL), if relevant:

## Additional context

Anything else that might help.

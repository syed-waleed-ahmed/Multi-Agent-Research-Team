# Contributing

Thanks for your interest in improving Multi-Agent Research Team. This guide
covers how to set up a development environment and the standards used in this
repository.

By participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Backend (Python 3.10+; 3.11+ recommended):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # engine + CLI + web app + tooling
cp .env.example .env             # add your Groq and Serper keys
```

Frontend (Node 22+):

```bash
cd frontend
npm ci
npx playwright install chromium  # only needed for end-to-end tests
```

Run everything locally:

```bash
research-team-web                # API (+ built site) on http://localhost:8000
cd frontend && npm run dev       # hot-reloading site; proxies /api to :8000
```

## Quality gates

All changes must pass the same checks that run in CI.

Backend:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # static type checking
pytest                  # tests (no network, no API keys)
```

Frontend (in `frontend/`):

```bash
npm run lint
npm run typecheck
npm run test            # Vitest unit/component tests
npm run build
npm run test:e2e        # Playwright: real API + deterministic test engine
```

`make check` runs the backend gates and `make frontend-check` the frontend
ones. Please run `ruff format .` before committing.

## Coding standards

- Keep functions fully type-annotated (Python and TypeScript strict mode).
- Keep the dependency direction intact: `web` → `crew` → `agents`/`tasks`/
  `providers`/`search`/`report` → `config`/`progress`/`exceptions`. The engine
  must never import the web layer, and lower layers must not import higher ones.
- Import heavy third-party libraries (CrewAI, LiteLLM) lazily inside functions
  so the CLI stays fast to start and the core stays unit-testable.
- Progress shown to users must come from real engine events. Never add
  simulated progress, fake data, or placeholder features.
- Everything that consumes a free quota (model requests, searches) must stay
  bounded and configurable; consider the impact on shared free tiers.
- Prefer small, single-responsibility modules and clear docstrings.
- Add or update tests for any behavior change.

## Testing notes

The suite is hermetic. Real CrewAI agents are exercised with
`litellm.completion` patched to scripted responses (see `tests/test_crew.py`);
the web layer runs on an in-memory database with an injected fake runner
(`tests/web_helpers.py`); end-to-end tests run the real API with a
deterministic test engine (`tests/e2e/server.py`). Test-only engines live
under `tests/` and never ship in the package. If you add a code path that calls
an external service, isolate it behind a factory or an injectable dependency so
it can be stubbed.

## Database changes

Schema changes need an Alembic migration:

```bash
alembic revision --autogenerate -m "describe the change"   # uses alembic.ini
```

Review the generated file in `src/research_team/web/migrations/versions/`.
Migrations run automatically when the web app starts.

## Commit and pull request process

1. Create a feature branch from `main`.
2. Make your change with accompanying tests and documentation.
3. Ensure the quality gates pass locally.
4. Open a pull request describing the motivation and the change. Keep the
   subject line concise and written in the imperative mood
   (for example, "Add retry jitter to the workflow").

## Reporting issues

When filing a bug, include the command you ran or the steps in the web app, the
expected and actual behavior, the relevant log output (run with `--verbose`),
the request id shown in API errors, and your Python and package versions.
Issue templates are provided to help.

Do not report security vulnerabilities as public issues. Follow the
[security policy](SECURITY.md) instead, and never include real API keys in any
issue, pull request, or log.

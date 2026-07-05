# Contributing

Thanks for your interest in improving Multi-Agent Research Team. This guide
covers how to set up a development environment and the standards used in this
repository.

By participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # add your Groq and Serper keys
```

## Quality gates

All changes must pass the same checks that run in CI:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # static type checking
pytest                  # tests
```

You can run every gate at once with `make check`. Please run `ruff format .`
before committing so formatting stays consistent.

## Coding standards

- Target Python 3.10+ and keep functions fully type-annotated.
- Keep the dependency direction intact: `cli` depends on `crew`, which depends
  on `agents`/`tasks`, which depend on `config`. Lower layers must not import
  higher layers.
- Import heavy third-party libraries (CrewAI, LiteLLM) lazily inside functions
  so the CLI stays fast to start and the core stays unit-testable.
- Prefer small, single-responsibility modules and clear docstrings.
- Add or update tests for any behavior change. Tests must not require network
  access or real API keys.

## Testing notes

The suite is hermetic. CrewAI-heavy paths are mocked, and the few tests that
construct real CrewAI objects do not make API calls. If you add a code path that
would call an external service, isolate it behind a factory or an injectable
dependency so it can be stubbed.

## Commit and pull request process

1. Create a feature branch from `main`.
2. Make your change with accompanying tests and documentation.
3. Ensure `make check` passes locally.
4. Open a pull request describing the motivation and the change. Keep the
   subject line concise and written in the imperative mood
   (for example, "Add retry jitter to the workflow").

## Reporting issues

When filing a bug, include the command you ran, the expected and actual
behavior, the relevant log output (run with `--verbose`), and your Python and
package versions. Issue templates are provided to help.

Do not report security vulnerabilities as public issues. Follow the
[security policy](SECURITY.md) instead, and never include real API keys in any
issue, pull request, or log.

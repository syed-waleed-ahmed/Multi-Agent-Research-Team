# Summary

<!-- What does this change do, and why? -->

## Related issues

<!-- e.g. Closes #123 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / internal change
- [ ] Documentation
- [ ] Build / CI / tooling

## Checklist

Backend:

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `mypy` passes
- [ ] `pytest` passes (added or updated tests where relevant)

Frontend (if `frontend/` changed):

- [ ] `npm run lint`, `npm run typecheck`, `npm run test` and `npm run build` pass
- [ ] `npm run test:e2e` passes for user-facing changes

General:

- [ ] Documentation updated (README / ARCHITECTURE / CHANGELOG / docs) if needed
- [ ] No secrets or credentials are included in the diff
- [ ] Free-tier impact considered (quota usage, limits, cold starts)

# Developer convenience targets.
# On Windows, run the underlying commands directly or use `make` via Git Bash / WSL.

.DEFAULT_GOAL := help
.PHONY: help install dev test lint format typecheck check run web frontend frontend-dev frontend-check e2e docker clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package (engine + CLI)
	pip install -e .

dev: ## Install with web app + development tooling
	pip install -e ".[dev]"

test: ## Run the backend test suite
	pytest

lint: ## Lint the Python code
	ruff check .

format: ## Auto-format the Python code
	ruff format .

typecheck: ## Run static type checking
	mypy

check: lint typecheck test ## Run all backend quality gates
	ruff format --check .

run: ## Run the CLI (usage: make run TOPIC="your topic")
	multi-agent-research-team --topic "$(TOPIC)"

web: ## Run the web app on http://localhost:8000 (build the frontend first)
	research-team-web

frontend: ## Install frontend dependencies and build the website
	cd frontend && npm ci && npm run build

frontend-dev: ## Run the Vite dev server (proxies /api to research-team-web on :8000)
	cd frontend && API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev

frontend-check: ## Frontend lint, type check, unit tests and build
	cd frontend && npm run lint && npm run typecheck && npm run test && npm run build

e2e: ## Playwright end-to-end tests (real API + deterministic test engine)
	cd frontend && npm run build && npm run test:e2e

docker: ## Build the production container image
	docker build -t multi-agent-research-team .

clean: ## Remove caches and build artifacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -rf frontend/dist frontend/test-results frontend/playwright-report
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true

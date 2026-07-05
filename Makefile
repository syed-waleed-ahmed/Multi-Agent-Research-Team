# Developer convenience targets.
# On Windows, run the underlying commands directly or use `make` via Git Bash / WSL.

.DEFAULT_GOAL := help
.PHONY: help install dev test lint format typecheck check run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package (runtime only)
	pip install -e .

dev: ## Install the package with development tooling
	pip install -e ".[dev]"

test: ## Run the test suite
	pytest

lint: ## Lint the codebase
	ruff check .

format: ## Auto-format the codebase
	ruff format .

typecheck: ## Run static type checking
	mypy

check: lint typecheck test ## Run all quality gates (lint + types + tests)
	ruff format --check .

run: ## Run the CLI (usage: make run TOPIC="your topic")
	multi-agent-research-team --topic "$(TOPIC)"

clean: ## Remove caches and build artifacts
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true

# Every lint, test, build and check lives here, and CI calls these same targets,
# so no command's flags are ever duplicated in a workflow file (BUILD_PLAN.md, §0 rule 11).
#
# Run `make` or `make help` for the list.

SHELL := bash
.DEFAULT_GOAL := help

COMPOSE := docker compose -f docker-compose.dev.yml
UV      := uv --directory backend
NPM     := npm --prefix frontend

# Local development and test database, started by `make db`. CI overrides this to
# point at its Postgres service container.
export DATABASE_URL ?= postgresql://doodle:doodle@127.0.0.1:5432/doodle

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help:
	@echo "Telephone Doodle"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

.PHONY: install
install: backend-install frontend-install ## Install backend and frontend dependencies

.PHONY: backend-install
backend-install: ## Sync the backend virtualenv from uv.lock
	$(UV) sync --locked

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies from package-lock.json
	$(NPM) ci

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

.PHONY: db
db: ## Start local Postgres and wait until it accepts connections
	$(COMPOSE) up -d --wait db

.PHONY: db-stop
db-stop: ## Stop local Postgres (the named volume keeps the data)
	$(COMPOSE) down

# ---------------------------------------------------------------------------
# Development servers
# ---------------------------------------------------------------------------

.PHONY: dev-backend
dev-backend: ## Run the API with reload on http://127.0.0.1:8000
	$(UV) run uvicorn main:app --reload --host 127.0.0.1 --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server (proxies /api and /ws to the backend)
	$(NPM) run dev

# ---------------------------------------------------------------------------
# Backend checks
# ---------------------------------------------------------------------------

.PHONY: backend-lint
backend-lint: ## Lint, format-check and check the package layering of the backend
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run lint-imports

.PHONY: backend-format
backend-format: ## Apply ruff's formatting and safe fixes to the backend
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

.PHONY: backend-test
backend-test: ## Run the backend test suite
	$(UV) run pytest

# ---------------------------------------------------------------------------
# Frontend checks
# ---------------------------------------------------------------------------

.PHONY: frontend-lint
frontend-lint: ## Lint the frontend (warnings fail)
	$(NPM) run lint

.PHONY: frontend-typecheck
frontend-typecheck: ## Type-check the frontend with tsc
	$(NPM) run typecheck

.PHONY: frontend-test
frontend-test: ## Run the frontend test suite
	$(NPM) run test

.PHONY: frontend-build
frontend-build: ## Build the production frontend bundle
	$(NPM) run build

# ---------------------------------------------------------------------------
# Umbrellas
# ---------------------------------------------------------------------------

.PHONY: lint
lint: backend-lint frontend-lint frontend-typecheck ## Lint everything

.PHONY: test
test: backend-test frontend-test ## Test everything

# ---------------------------------------------------------------------------
# CI entry points: one per area, matching the jobs in .github/workflows/ci.yml
# ---------------------------------------------------------------------------

.PHONY: ci-backend
ci-backend: backend-lint backend-test ## CI: backend lint and tests

.PHONY: ci-frontend
ci-frontend: frontend-lint frontend-typecheck frontend-test frontend-build ## CI: frontend checks and build

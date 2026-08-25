.PHONY: help dev build stop clean migrate seed test test-backend test-frontend logs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start all services in development mode
	docker compose up

build: ## Build all Docker images
	docker compose build

stop: ## Stop all services
	docker compose down

clean: ## Stop services and remove volumes (DESTRUCTIVE)
	docker compose down -v --remove-orphans

migrate: ## Run Alembic migrations
	docker compose exec backend alembic upgrade head

seed: ## Run seed data script
	docker compose exec backend python -m app.seed

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend pytest suite
	docker compose exec backend pytest -v

test-frontend: ## Run frontend Jest suite
	docker compose exec frontend npm test -- --watchAll=false

logs: ## Tail all service logs
	docker compose logs -f

shell-backend: ## Open a shell in the backend container
	docker compose exec backend bash

shell-db: ## Open psql in the postgres container
	docker compose exec postgres psql -U postgres -d ledgerpilot

# ── Local development (without Docker) ───────────────────────────────────────
local-backend: ## Run backend locally (requires local Postgres + .env)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

local-frontend: ## Run frontend locally
	cd frontend && npm run dev

local-migrate: ## Run migrations locally
	cd backend && alembic upgrade head

local-seed: ## Seed database locally
	cd backend && python -m app.seed

local-test-backend: ## Run backend tests locally
	cd backend && pytest -v

local-test-frontend: ## Run frontend tests locally
	cd frontend && npm test -- --watchAll=false

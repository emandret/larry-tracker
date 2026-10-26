SERVICES := location-service

.PHONY: help dev prod down logs smoke test lint fmt

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

dev: ## Run the stack, syncing source edits into the containers
	docker compose up --build --watch

prod: ## Build self-contained images and run detached
	docker compose up --build -d

down: ## Stop the stack
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

smoke: ## Check the running stack answers on every route
	@./scripts/smoke.sh

test: ## Run each service's tests
	@set -e; for s in $(SERVICES); do (cd "$$s" && uv run pytest); done

lint: ## Run ruff check on each service
	@set -e; for s in $(SERVICES); do (cd "$$s" && uv run ruff check .); done

fmt: ## Run ruff format on each service
	@set -e; for s in $(SERVICES); do (cd "$$s" && uv run ruff format .); done

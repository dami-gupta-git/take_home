.PHONY: install lint lint-fix typecheck test ci up down logs migrate

# Install dev dependencies for both services (see setup.md for venv setup first)
install:
	cd backend && pip install -r requirements-dev.txt
	cd microservice && pip install -r requirements-dev.txt

# Format and lint both services
lint:
	cd backend && ruff format . && ruff check .
	cd microservice && ruff format . && ruff check .

# Format, lint, and auto-fix both services
lint-fix:
	cd backend && ruff format . && ruff check --fix .
	cd microservice && ruff format . && ruff check --fix .

# Run mypy type checks for both services
typecheck:
	cd backend && mypy .
	cd microservice && mypy .

# Run tests for both services
test:
	cd backend && pytest
	cd microservice && pytest

# Run full CI pipeline: lint + typecheck + test
ci: lint typecheck test

# Apply all pending Alembic migrations (requires Postgres running via make up)
migrate:
	cd backend && .venv/bin/alembic upgrade head

# Docker Compose targets
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

.PHONY: install lint lint-fix typecheck test ci up down logs

install:
	cd backend && pip install -r requirements-dev.txt
	cd microservice && pip install -r requirements-dev.txt

lint:
	cd backend && ruff format . && ruff check .
	cd microservice && ruff format . && ruff check .

lint-fix:
	cd backend && ruff format . && ruff check --fix .
	cd microservice && ruff format . && ruff check --fix .

typecheck:
	cd backend && mypy .
	cd microservice && mypy .

test:
	cd backend && pytest
	cd microservice && pytest

ci: lint typecheck test

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

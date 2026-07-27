SHELL := /bin/bash
.ONESHELL:

.PHONY: lint format typecheck test-unit test-integration test-all check

lint:
	uv run ruff check src tests alembic

format:
	uv run ruff format src tests alembic

typecheck:
	uv run mypy

test-unit:
	uv run pytest tests/unit

test-integration:
	set -euo pipefail
	trap 'docker compose -f docker-compose.test.yml down --volumes --remove-orphans' EXIT
	docker compose -f docker-compose.test.yml up --wait --detach
	test_database_url='postgresql+asyncpg://mood_tracker_test:mood_tracker_test@localhost:54329/mood_tracker_test'
	uv run alembic -x database_url="$$test_database_url" -x expected_database=mood_tracker_test upgrade head
	TEST_DATABASE_URL="$$test_database_url" uv run pytest tests/integration

test-all: test-unit test-integration

check: lint typecheck test-all

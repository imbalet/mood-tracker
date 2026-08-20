SHELL := /bin/bash
.ONESHELL:

TEST_COMPOSE := docker compose --project-name mood-tracker-integration -f docker-compose.test.yml

.PHONY: lint format typecheck test-unit test-integration test-all check

lint:
	uv run ruff check src tests alembic
	uv run mypy

format:
	uv run ruff format src tests alembic && \
	uv run ruff check src tests alembic --fix

test-unit:
	uv run pytest tests/unit

test-integration:
	set -euo pipefail
	trap '$(TEST_COMPOSE) down --volumes --remove-orphans' EXIT
	$(TEST_COMPOSE) up --wait --detach
	test_database_url='postgresql+asyncpg://mood_tracker_test:mood_tracker_test@localhost:54329/mood_tracker_test'
	uv run alembic -x database_url="$$test_database_url" -x expected_database=mood_tracker_test upgrade head
	TEST_DATABASE_URL="$$test_database_url" uv run pytest tests/integration

test-all: test-unit test-integration

check: lint typecheck test-all

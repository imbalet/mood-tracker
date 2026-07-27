SHELL := /bin/bash
.ONESHELL:

.PHONY: lint format typecheck test-unit test-integration test-all check

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy

test-unit:
	uv run pytest tests/unit

test-integration:
	set -euo pipefail
	trap 'docker compose -f docker-compose.test.yml down --volumes --remove-orphans' EXIT
	docker compose -f docker-compose.test.yml up --wait --detach
	TEST_DATABASE_URL=postgresql+asyncpg://mood_tracker_test:mood_tracker_test@localhost:54329/mood_tracker_test uv run pytest tests/integration

test-all: test-unit test-integration

check: lint typecheck test-all

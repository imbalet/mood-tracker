"""Shared deterministic fixtures for all test layers."""

from datetime import UTC, date, datetime

import pytest

from tests.factories import DayFactory, FieldFactory, ReferenceDayFactory, UserFactory


@pytest.fixture
def fixed_now() -> datetime:
    """Return one timezone-aware timestamp for deterministic assertions."""
    return datetime(2025, 1, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def fixed_date() -> date:
    """Return one user-local calendar date for deterministic assertions."""
    return date(2025, 1, 2)


@pytest.fixture
def day_factory() -> DayFactory:
    """Return a builder for user-day aggregates."""
    return DayFactory()


@pytest.fixture
def field_factory() -> FieldFactory:
    """Return a builder for field aggregates."""
    return FieldFactory()


@pytest.fixture
def reference_day_factory() -> ReferenceDayFactory:
    """Return a builder for reference-day history entries."""
    return ReferenceDayFactory()


@pytest.fixture
def user_factory() -> UserFactory:
    """Return a builder for user profiles."""
    return UserFactory()

"""Persistence protocols expressed in domain aggregates."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from mood_tracker.domain.entities import Day, Field, ReferenceDays, UserProfile


class UserRepository(Protocol):
    """Persist and retrieve user profiles."""

    async def get(self, user_id: UUID) -> UserProfile | None: ...

    async def get_by_telegram_id(self, telegram_id: int) -> UserProfile | None: ...

    async def add(self, user: UserProfile) -> None: ...

    async def save(self, user: UserProfile) -> None: ...


class FieldRepository(Protocol):
    """Persist fields including their full version history."""

    async def get(self, user_id: UUID, field_id: UUID) -> Field | None: ...

    async def list_for_user(self, user_id: UUID) -> Sequence[Field]: ...

    async def add(self, field: Field) -> None: ...

    async def save(self, field: Field) -> None: ...


class DayRepository(Protocol):
    """Persist one day aggregate for each user-local date."""

    async def get(self, user_id: UUID, day_id: UUID) -> Day | None: ...

    async def get_by_date(self, user_id: UUID, day_date: date) -> Day | None: ...

    async def get_many(
        self, user_id: UUID, day_ids: Sequence[UUID]
    ) -> Sequence[Day]: ...

    async def add(self, day: Day) -> None: ...

    async def save(self, day: Day) -> None: ...


class ReferenceDaysRepository(Protocol):
    """Persist current reference pointers and their immutable history."""

    async def get(self, user_id: UUID) -> ReferenceDays | None: ...

    async def save(self, reference_days: ReferenceDays) -> None: ...

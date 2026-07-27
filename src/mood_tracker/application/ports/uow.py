"""Transactional persistence boundary for application use cases."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from mood_tracker.application.ports.repositories import (
    DayRepository,
    FieldRepository,
    ReferenceDaysRepository,
    UserRepository,
)


class UnitOfWork(Protocol):
    """Coordinate repositories and one atomic persistence transaction."""

    users: UserRepository
    fields: FieldRepository
    days: DayRepository
    reference_days: ReferenceDaysRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

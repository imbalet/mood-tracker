"""Transactional persistence boundary for application use cases."""

from types import TracebackType
from typing import Protocol, Self

from mood_tracker.application.ports.repositories import (
    DayRepository,
    EventRepository,
    FieldRepository,
    NotificationDeliveryRepository,
    NotificationSettingsRepository,
    QuestionnaireRepository,
    ReferenceDaysRepository,
    UserRepository,
)


class UnitOfWork(Protocol):
    """Coordinate repositories and one atomic persistence transaction."""

    users: UserRepository
    fields: FieldRepository
    questionnaires: QuestionnaireRepository
    days: DayRepository
    events: EventRepository
    reference_days: ReferenceDaysRepository
    notification_settings: NotificationSettingsRepository
    notification_deliveries: NotificationDeliveryRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

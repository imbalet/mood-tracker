"""Persistence protocols expressed in domain aggregates."""

# TODO: посмотреть слоп

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from mood_tracker.domain.entities import (
    Day,
    Event,
    Field,
    NotificationSettings,
    Questionnaire,
    ReferenceDays,
    UserProfile,
)
from mood_tracker.domain.enums import QuestionnaireKind


class NotificationDeliveryStatus(StrEnum):
    claimed = "claimed"
    sent = "sent"


@dataclass(frozen=True)
class NotificationDelivery:
    reminder_number: int
    status: NotificationDeliveryStatus


class NotificationSettingsRepository(Protocol):
    async def get(self, user_id: UUID) -> NotificationSettings | None: ...

    async def add(self, settings: NotificationSettings) -> None: ...

    async def save(self, settings: NotificationSettings) -> None: ...


class NotificationDeliveryRepository(Protocol):
    async def get_deliveries(
        self, user_id: UUID, local_date: date
    ) -> list[NotificationDelivery]: ...

    async def try_claim(
        self,
        user_id: UUID,
        local_date: date,
        reminder_number: int,
        claim_timeout: timedelta,
    ) -> bool: ...

    async def mark_sent(
        self,
        user_id: UUID,
        local_date: date,
        reminder_number: int,
        sent_at: datetime,
    ) -> None: ...


class UserRepository(Protocol):
    """Persist and retrieve user profiles."""

    async def get(self, user_id: UUID) -> UserProfile | None: ...

    async def get_by_telegram_id(self, telegram_id: int) -> UserProfile | None: ...

    async def list_all(self) -> Sequence[UserProfile]: ...

    async def add(self, user: UserProfile) -> None: ...

    async def save(self, user: UserProfile) -> None: ...


class FieldRepository(Protocol):
    """Persist fields including their full version history."""

    async def get(self, user_id: UUID, field_id: UUID) -> Field | None: ...

    async def list_for_user(self, user_id: UUID) -> Sequence[Field]: ...

    async def add(self, field: Field) -> None: ...

    async def save(self, field: Field) -> None: ...


class QuestionnaireRepository(Protocol):
    """Persist the field placements of a single user questionnaire."""

    async def get(
        self, user_id: UUID, kind: QuestionnaireKind
    ) -> Questionnaire | None: ...

    async def add(self, questionnaire: Questionnaire) -> None: ...

    async def save(self, questionnaire: Questionnaire) -> None: ...


class DayRepository(Protocol):
    """Persist one day aggregate for each user-local date."""

    async def get(self, user_id: UUID, day_id: UUID) -> Day | None: ...

    async def get_by_date(self, user_id: UUID, day_date: date) -> Day | None: ...

    async def get_many(
        self, user_id: UUID, day_ids: Sequence[UUID]
    ) -> Sequence[Day]: ...

    async def list_for_month(self, user_id: UUID, month: date) -> Sequence[Day]: ...

    async def add(self, day: Day) -> None: ...

    async def save(self, day: Day) -> None: ...


class EventRepository(Protocol):
    """Persist standalone, owner-scoped contextual events."""

    async def get(self, user_id: UUID, event_id: UUID) -> Event | None: ...

    async def list_for_date(
        self, user_id: UUID, event_date: date
    ) -> Sequence[Event]: ...

    async def add(self, event: Event) -> None: ...

    async def save(self, event: Event) -> None: ...


class ReferenceDaysRepository(Protocol):
    """Persist current reference pointers and their immutable history."""

    async def get(self, user_id: UUID) -> ReferenceDays | None: ...

    async def save(self, reference_days: ReferenceDays) -> None: ...

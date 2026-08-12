"""Event-related application contracts."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from mood_tracker.domain.value_objects import UserTimezone


@dataclass(frozen=True, slots=True)
class GetEventsForDate:
    user_id: UUID
    event_date: date


@dataclass(frozen=True, slots=True)
class CreateQuickEvent:
    user_id: UUID
    text: str


@dataclass(frozen=True, slots=True)
class CreateEvent:
    """Create a regular event at a selected instant."""

    user_id: UUID
    occurred_at: datetime
    occurred_timezone: UserTimezone


@dataclass(frozen=True, slots=True)
class GetEvent:
    user_id: UUID
    event_id: UUID


@dataclass(frozen=True, slots=True)
class SaveEventValue:
    user_id: UUID
    event_id: UUID
    field_id: UUID
    value: int | str


@dataclass(frozen=True, slots=True)
class SkipEventField:
    user_id: UUID
    event_id: UUID
    field_id: UUID


@dataclass(frozen=True, slots=True)
class CompleteEvent:
    user_id: UUID
    event_id: UUID


@dataclass(frozen=True, slots=True)
class ChangeEventTime:
    user_id: UUID
    event_id: UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class DeleteEvent:
    user_id: UUID
    event_id: UUID

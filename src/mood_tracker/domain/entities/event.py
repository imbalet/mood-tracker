"""Timestamped contextual events and their versioned values."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.entities.questionnaire import Answer, QuestionnaireResponse
from mood_tracker.domain.enums import EventStatus
from mood_tracker.domain.value_objects import UserTimezone, require_utc


@dataclass(slots=True)
class Event:
    """One user-owned event, independent from the daily aggregate."""

    id: UUID
    user_id: UUID
    occurred_at: datetime
    occurred_timezone: UserTimezone
    status: EventStatus = EventStatus.DRAFT
    completed_at: datetime | None = None
    deleted_at: datetime | None = None
    response: QuestionnaireResponse = field(default_factory=QuestionnaireResponse)

    def __post_init__(self) -> None:
        self.occurred_at = require_utc(self.occurred_at, "Event occurrence time")
        if self.completed_at is not None:
            self.completed_at = require_utc(self.completed_at, "Event completion time")
        if self.deleted_at is not None:
            self.deleted_at = require_utc(self.deleted_at, "Event deletion time")

    def save_value(self, field_version: FieldVersion, value: int | str) -> Answer:
        return self.response.answer(field_version=field_version, value=value)

    def skip_field(self, field_version: FieldVersion) -> None:
        self.response.skip(field_version=field_version)

    def has_completed_step(self, field_id: UUID) -> bool:
        return self.response.has_completed_step(field_id=field_id)

    def complete(self, completed_at: datetime) -> None:
        self.status = EventStatus.COMPLETE
        self.completed_at = require_utc(completed_at, "Event completion time")

    def change_time(self, occurred_at: datetime) -> None:
        self.occurred_at = require_utc(occurred_at, "Event occurrence time")

    def delete(self, deleted_at: datetime) -> None:
        self.deleted_at = require_utc(deleted_at, "Event deletion time")

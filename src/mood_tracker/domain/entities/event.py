"""Timestamped contextual events and their versioned values."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.day import DayFieldProgress, DayValue
from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.enums import EventStatus, QuestionnaireFieldRole


@dataclass(frozen=True, slots=True)
class EventQuestionnaireField:
    """Immutable placement snapshot captured when an event is created."""

    field_id: UUID
    sort_order: int
    is_enabled: bool
    is_required: bool
    role: QuestionnaireFieldRole


@dataclass(slots=True)
class Event:
    """One user-owned event, independent from the daily aggregate."""

    id: UUID
    user_id: UUID
    occurred_at: datetime
    occurred_timezone: str
    status: EventStatus = EventStatus.DRAFT
    completed_at: datetime | None = None
    deleted_at: datetime | None = None
    values: dict[UUID, DayValue] = field(default_factory=dict)
    progress: dict[UUID, DayFieldProgress] = field(default_factory=dict)
    questionnaire_fields: dict[UUID, EventQuestionnaireField] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            msg = "Event occurrence time must be timezone-aware"
            raise ValueError(msg)

    def save_value(self, field_version: FieldVersion, value: int | str) -> DayValue:
        """Validate and save one answer with its semantic version."""
        event_value = DayValue.from_input(self.id, field_version, value)
        self.values[field_version.field_id] = event_value
        self.progress[field_version.field_id] = DayFieldProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=False,
        )
        return event_value

    def skip_field(self, field_version: FieldVersion) -> None:
        """Mark any optional event step as deliberately skipped."""
        self.values.pop(field_version.field_id, None)
        self.progress[field_version.field_id] = DayFieldProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=True,
        )

    def has_completed_step(self, field_id: UUID) -> bool:
        return field_id in self.progress

    def ordered_questionnaire_fields(self) -> tuple[EventQuestionnaireField, ...]:
        return tuple(
            sorted(self.questionnaire_fields.values(), key=lambda item: item.sort_order)
        )

    def complete(self, completed_at: datetime) -> None:
        self.status = EventStatus.COMPLETE
        self.completed_at = completed_at

    def change_time(self, occurred_at: datetime) -> None:
        if occurred_at.tzinfo is None:
            msg = "Event occurrence time must be timezone-aware"
            raise ValueError(msg)
        self.occurred_at = occurred_at

    def delete(self, deleted_at: datetime) -> None:
        self.deleted_at = deleted_at

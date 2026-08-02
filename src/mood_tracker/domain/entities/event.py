"""Timestamped contextual events and their versioned values."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.entities.questionnaire import Answer, QuestionnaireResponse
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
    response: QuestionnaireResponse = field(default_factory=QuestionnaireResponse)
    questionnaire_fields: dict[UUID, EventQuestionnaireField] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            msg = "Event occurrence time must be timezone-aware"
            raise ValueError(msg)

    def save_value(self, field_version: FieldVersion, value: int | str) -> Answer:
        return self.response.answer(field_version=field_version, value=value)

    def skip_field(self, field_version: FieldVersion) -> None:
        self.response.skip(field_version=field_version)

    def has_completed_step(self, field_id: UUID) -> bool:
        return self.response.has_completed_step(field_id=field_id)

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

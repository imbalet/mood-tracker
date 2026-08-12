"""Diary day and reference-decision application contracts."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date
from uuid import UUID

from mood_tracker.domain.entities import Day, Field
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import ReferenceType


@dataclass(frozen=True, slots=True)
class GetDay:
    """Read one existing day by date without creating a draft."""

    user_id: UUID
    day_date: date | None = None


@dataclass(frozen=True, slots=True)
class SaveDayValue:
    """Save a raw answer using the field's current semantic version."""

    user_id: UUID
    day_date: date
    field_id: UUID
    value: int | str


@dataclass(frozen=True, slots=True)
class SkipDayText:
    """Explicitly skip a Text step, creating the day if needed."""

    user_id: UUID
    day_date: date
    field_id: UUID


@dataclass(frozen=True, slots=True)
class ConfirmReference:
    """Confirm or reject a best/worst comparison requested by the application."""

    user_id: UUID
    day_id: UUID
    type: ReferenceType
    is_new_record: bool


@dataclass(frozen=True, slots=True)
class DayForm:
    """A day plus the next active field the user should answer."""

    day_date: date
    day: Day | None
    fields: tuple[Field, ...]
    next_field: Field | None
    placements: dict[UUID, QuestionnaireField] = dataclass_field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReferenceReview:
    """A requested user decision about a boundary state value."""

    day_id: UUID
    type: ReferenceType
    previous_reference_day_id: UUID | None

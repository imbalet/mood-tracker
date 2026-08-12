"""Calendar application contracts."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date
from uuid import UUID

from mood_tracker.domain.entities import Day, Field, ReferenceDays
from mood_tracker.domain.entities.questionnaire import QuestionnaireField


@dataclass(frozen=True, slots=True)
class GetMonthCalendar:
    """Read one user's diary data required to render a calendar month."""

    user_id: UUID
    month: date


@dataclass(frozen=True, slots=True, kw_only=True)
class MonthCalendar:
    """Owned days and fields used by calendar presentation."""

    month: date
    days: tuple[Day, ...]
    fields: tuple[Field, ...]
    references: ReferenceDays | None
    placements: dict[UUID, QuestionnaireField] = dataclass_field(default_factory=dict)

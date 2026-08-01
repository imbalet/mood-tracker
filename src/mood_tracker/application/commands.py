"""Immutable input and output contracts for core application use cases."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from mood_tracker.domain.entities import (
    Day,
    Field,
    FieldConfig,
    FieldDisplayConfig,
    ReferenceDay,
    ReferenceDays,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    QuestionnaireKind,
    ReferenceType,
)
from mood_tracker.domain.value_objects import UserTimezone


class MoveDirection(StrEnum):
    """One-step direction in a user's field order."""

    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class RegisterUser:
    """Register a Telegram user or return their existing profile."""

    telegram_id: int
    timezone: UserTimezone


@dataclass(frozen=True, slots=True)
class GetUserByTelegramId:
    """Look up a profile owned by a Telegram account."""

    telegram_id: int


@dataclass(frozen=True, slots=True)
class SetTimezone:
    """Change one user's IANA timezone."""

    user_id: UUID
    timezone: UserTimezone


@dataclass(frozen=True, slots=True)
class CreateField:
    """Create one custom field and its initial semantic version."""

    user_id: UUID
    name: str
    config: FieldConfig
    display_config: FieldDisplayConfig
    sort_order: int
    kind: QuestionnaireKind = QuestionnaireKind.DAY


@dataclass(frozen=True, slots=True)
class RenameField:
    """Rename one user-owned field."""

    user_id: UUID
    field_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class SetFieldDisplay:
    """Replace one field's current display configuration."""

    user_id: UUID
    field_id: UUID
    display_config: FieldDisplayConfig


@dataclass(frozen=True, slots=True)
class AddFieldVersion:
    """Append a new semantic configuration to one field."""

    user_id: UUID
    field_id: UUID
    config: FieldConfig


@dataclass(frozen=True, slots=True)
class ListQuestionnaireFields:
    """Read fields assigned to one explicit questionnaire."""

    user_id: UUID
    kind: QuestionnaireKind


@dataclass(frozen=True, slots=True)
class QuestionnaireFieldItem:
    """A semantic field resolved with its placement in one questionnaire."""

    field: Field
    placement: QuestionnaireField


@dataclass(frozen=True, slots=True)
class AttachFieldToQuestionnaire:
    """Attach an existing semantic field to one questionnaire."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    sort_order: int
    is_required: bool = False


@dataclass(frozen=True, slots=True)
class DetachFieldFromQuestionnaire:
    """Remove a non-system field from one questionnaire only."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind


@dataclass(frozen=True, slots=True)
class SetQuestionnaireFieldEnabled:
    """Hide or restore a field without deleting its historical values."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    is_enabled: bool


@dataclass(frozen=True, slots=True)
class SetQuestionnaireFieldRequired:
    """Change whether a questionnaire step may be skipped."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    is_required: bool


@dataclass(frozen=True, slots=True)
class MoveQuestionnaireField:
    """Move a field inside one explicit questionnaire."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    direction: MoveDirection


@dataclass(frozen=True, slots=True)
class DeleteField:
    """Soft-delete a semantic field globally."""

    user_id: UUID
    field_id: UUID


@dataclass(frozen=True, slots=True)
class GetDay:
    """Read one existing day by date without creating a draft."""

    user_id: UUID
    day_date: date | None = None


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
    occurred_timezone: str


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


@dataclass(frozen=True, slots=True)
class GetMonthCalendar:
    """Read one user's diary data required to render a calendar month."""

    user_id: UUID
    month: date


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
class GetReferenceHistory:
    """Read current reference chains and the immutable full event journal."""

    user_id: UUID


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


@dataclass(frozen=True, slots=True)
class ReferenceHistory:
    """Current best/worst chains alongside every confirmed historical event."""

    best_chain: tuple[ReferenceDay, ...]
    worst_chain: tuple[ReferenceDay, ...]
    all_events: tuple[ReferenceDay, ...]


@dataclass(frozen=True, slots=True)
class MonthCalendar:
    """Owned days and fields used by calendar presentation."""

    month: date
    days: tuple[Day, ...]
    fields: tuple[Field, ...]
    references: ReferenceDays | None
    placements: dict[UUID, QuestionnaireField] = dataclass_field(default_factory=dict)

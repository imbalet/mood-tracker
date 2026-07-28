"""Immutable input and output contracts for core application use cases."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from mood_tracker.domain.entities import (
    Day,
    Field,
    FieldConfig,
    FieldDisplayConfig,
    ReferenceDay,
)
from mood_tracker.domain.enums import FieldStatus, ReferenceType
from mood_tracker.domain.value_objects import UserTimezone


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


@dataclass(frozen=True, slots=True)
class RenameField:
    """Rename one user-owned field."""

    user_id: UUID
    field_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class SetFieldStatus:
    """Change one field's active/inactive/hidden lifecycle."""

    user_id: UUID
    field_id: UUID
    status: FieldStatus


@dataclass(frozen=True, slots=True)
class SetFieldDisplay:
    """Replace one field's current display configuration."""

    user_id: UUID
    field_id: UUID
    display_config: FieldDisplayConfig


@dataclass(frozen=True, slots=True)
class SetFieldSortOrder:
    """Change one field's display and questionnaire position."""

    user_id: UUID
    field_id: UUID
    sort_order: int


@dataclass(frozen=True, slots=True)
class AddFieldVersion:
    """Append a new semantic configuration to one field."""

    user_id: UUID
    field_id: UUID
    config: FieldConfig


@dataclass(frozen=True, slots=True)
class ListFields:
    """Read all fields owned by one user in display order."""

    user_id: UUID


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

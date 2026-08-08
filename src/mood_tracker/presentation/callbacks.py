"""Typed compact callback payloads for diary interactions."""

import base64
from enum import StrEnum
from typing import Any, override
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from pydantic import field_validator

from mood_tracker.application.commands import MoveDirection
from mood_tracker.domain.enums import (
    FieldStatus,
    FieldType,
    QuestionnaireKind,
    ReferenceType,
)


class MenuSection(StrEnum):
    """Top-level screens available from the inline interface."""

    HOME = "home"
    TODAY = "today"
    FIELDS = "fields"
    DATES = "dates"
    CALENDAR = "calendar"


class CalendarImageAction(StrEnum):
    """Navigate an already rendered PNG month."""

    PREVIOUS = "previous"
    NEXT = "next"


class FieldAction(StrEnum):
    """Actions performed from an individual field card."""

    OPEN = "open"
    RENAME = "rename"
    VERSION = "version"
    ORDER = "order"
    EMOJI = "emoji"
    CLEAR_EMOJI = "clear_emoji"
    TOGGLE_CALENDAR = "toggle_calendar"
    PALETTE = "palette"
    BACK = "back"


class FieldsListAction(StrEnum):
    """Actions that do not require selecting an existing field."""

    CREATE = "create"
    ORDER = "order"
    SELECT = "select"
    ATTACH = "attach"


class FieldsListCallback(CallbackData, prefix="fields"):
    """Open a list-level field-management screen."""

    action: FieldsListAction
    kind: QuestionnaireKind = QuestionnaireKind.DAY


class FieldCallback(CallbackData, prefix="field"):
    """Address an owned field and one of its presentation actions."""

    action: FieldAction
    field_id: UUID
    kind: QuestionnaireKind = QuestionnaireKind.DAY


class FieldCreateCallback(CallbackData, prefix="field_create"):
    """Start custom-field creation with a fixed semantic type."""

    type: FieldType
    kind: QuestionnaireKind = QuestionnaireKind.DAY


class AttachFieldCallback(CallbackData, prefix="field_attach"):
    """Attach a field from the other questionnaire."""

    field_id: UUID
    kind: QuestionnaireKind


class QuestionnaireFieldAction(StrEnum):
    """Placement-only actions from a field card."""

    TOGGLE_REQUIRED = "toggle_required"
    DETACH = "detach"


class QuestionnaireFieldCallback(CallbackData, prefix="questionnaire_field"):
    """Address an existing placement in an explicit questionnaire."""

    action: QuestionnaireFieldAction
    field_id: UUID
    kind: QuestionnaireKind


class FieldStatusCallback(CallbackData, prefix="field_status"):
    """Set a non-core field lifecycle state."""

    field_id: UUID
    status: FieldStatus
    kind: QuestionnaireKind = QuestionnaireKind.DAY


class FieldMoveCallback(CallbackData, prefix="field_move"):
    """Move one field one position within its owner's order."""

    field_id: UUID
    direction: MoveDirection
    kind: QuestionnaireKind = QuestionnaireKind.DAY


class OrdinalDraftAction(StrEnum):
    """Actions available while composing ordinal labels."""

    REMOVE = "remove"
    RESET = "reset"
    FINISH = "finish"


class OrdinalBaseCallback(CallbackData, prefix="ordinal_base"):
    """Choose whether the first ordinal value is the hidden zero marker."""

    value: int


class OrdinalDraftCallback(CallbackData, prefix="ordinal"):
    """Modify an in-progress ordinal configuration stored in FSM data."""

    action: OrdinalDraftAction


class PalettePreset(StrEnum):
    """Named palette choices understandable without raw color codes."""

    WARM = "warm"
    FOREST = "forest"
    COOL = "cool"
    CUSTOM = "custom"


class PaletteCallback(CallbackData, prefix="palette"):
    """Select a predefined or custom core-state palette."""

    field_id: UUID
    preset: PalettePreset


class TimezoneCallback(CallbackData, prefix="timezone"):
    """Choose a predefined timezone or the manual-input path."""

    timezone: str


class MenuCallback(CallbackData, prefix="menu"):
    """Navigate between top-level inline screens."""

    section: MenuSection


class CalendarImageCallback(CallbackData, prefix="month_calendar"):
    """Select a neighbouring month for a PNG calendar."""

    action: CalendarImageAction
    year: int
    month: int


class DayValueCallback(CallbackData, prefix="value"):
    """Save a numeric answer for one field on one date."""

    day: str
    field_id: UUID
    value: int


class OpenDayCallback(CallbackData, prefix="day"):
    """Return to one day's interactive summary card."""

    day: str


class SkipTextCallback(CallbackData, prefix="skip"):
    """Skip a Text field for one date."""

    day: str
    field_id: UUID


class ReferenceCallback(CallbackData, prefix="reference"):
    """Confirm or reject a candidate best/worst day."""

    day_id: UUID
    type: ReferenceType
    is_new_record: bool


class EditDayValueCallback(CallbackData, prefix="edit"):
    """Open an existing field value for editing."""

    day: str
    field_id: UUID


class EventAction(StrEnum):
    START = "start"
    QUICK_TEXT = "quick_text"
    OPEN = "open"
    CONTINUE = "continue"
    COMPLETE = "complete"
    CHANGE_TIME = "change_time"
    DELETE = "delete"
    CONFIRM_DELETE = "confirm_delete"


class EventCallback(CallbackData, prefix="event"):
    action: EventAction
    event_id: UUID | None = None
    day: str | None = None


class EventTimeCallback(CallbackData, prefix="event_time"):
    day: str
    now: bool


def encode_uuid(value: UUID) -> str:
    return base64.urlsafe_b64encode(value.bytes).rstrip(b"=").decode()


def decode_uuid(value: str) -> UUID:
    return UUID(bytes=base64.urlsafe_b64decode(value + "=="))


class EventValueCallback(CallbackData, prefix="evnt_vle"):
    event_id: UUID
    field_id: UUID
    value: int

    # TODO: refactor
    @override
    def _encode_value(self, key: str, value: Any) -> str:
        if isinstance(value, UUID):
            return encode_uuid(value)

        return super()._encode_value(key, value)

    @field_validator("event_id", "field_id", mode="before")
    @classmethod
    def decode_compact_uuid(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) == 22:
            return decode_uuid(value)

        return value


class SkipEventFieldCallback(CallbackData, prefix="evntskp"):
    event_id: UUID
    field_id: UUID

    # TODO: refactor
    @override
    def _encode_value(self, key: str, value: Any) -> str:
        if isinstance(value, UUID):
            return encode_uuid(value)

        return super()._encode_value(key, value)

    @field_validator("event_id", "field_id", mode="before")
    @classmethod
    def decode_compact_uuid(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) == 22:
            return decode_uuid(value)

        return value

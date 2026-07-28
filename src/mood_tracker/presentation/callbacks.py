"""Typed compact callback payloads for diary interactions."""

from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData

from mood_tracker.application.commands import MoveDirection
from mood_tracker.domain.enums import FieldStatus, FieldType, ReferenceType


class MenuSection(StrEnum):
    """Top-level screens available from the inline interface."""

    HOME = "home"
    TODAY = "today"
    FIELDS = "fields"


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


class FieldsListCallback(CallbackData, prefix="fields"):
    """Open a list-level field-management screen."""

    action: FieldsListAction


class FieldCallback(CallbackData, prefix="field"):
    """Address an owned field and one of its presentation actions."""

    action: FieldAction
    field_id: UUID


class FieldCreateCallback(CallbackData, prefix="field_create"):
    """Start custom-field creation with a fixed semantic type."""

    type: FieldType


class FieldStatusCallback(CallbackData, prefix="field_status"):
    """Set a non-core field lifecycle state."""

    field_id: UUID
    status: FieldStatus


class FieldMoveCallback(CallbackData, prefix="field_move"):
    """Move one field one position within its owner's order."""

    field_id: UUID
    direction: MoveDirection


class OrdinalDraftAction(StrEnum):
    """Actions available while composing ordinal labels."""

    ADD = "add"
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


class DayValueCallback(CallbackData, prefix="value"):
    """Save a numeric answer for one field on one date."""

    day: str
    field_id: UUID
    value: int


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

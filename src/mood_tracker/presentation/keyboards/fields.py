"""Small input-step keyboards for field creation and versioning."""

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.domain.enums import FieldType
from mood_tracker.presentation.callbacks import (
    FieldCreateCallback,
    MenuCallback,
    MenuSection,
    OrdinalBaseCallback,
    OrdinalDraftAction,
    OrdinalDraftCallback,
)
from mood_tracker.presentation.constants import TextKey
from mood_tracker.presentation.utils import KeyboardBuilder


def field_type_keyboard() -> InlineKeyboardMarkup:
    """Build semantic-type choices for a newly created custom field."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (TextKey.FIELD_TYPE_SCALE, FieldCreateCallback(type=FieldType.SCALE))
    )
    builder.row_buttons_tuple(
        (TextKey.FIELD_TYPE_ORDINAL, FieldCreateCallback(type=FieldType.ORDINAL))
    )
    builder.row_buttons_tuple(
        (TextKey.FIELD_TYPE_TEXT, FieldCreateCallback(type=FieldType.TEXT))
    )
    builder.row_buttons_tuple((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
    return builder.as_markup()


def ordinal_base_keyboard() -> InlineKeyboardMarkup:
    """Choose the ordinal numbering rule through calendar behavior."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (TextKey.ORDINAL_HIDDEN_ZERO, OrdinalBaseCallback(value=0))
    )
    builder.row_buttons_tuple(
        (TextKey.ORDINAL_VISIBLE_ONE, OrdinalBaseCallback(value=1))
    )
    return builder.as_markup()


def ordinal_draft_keyboard(label_count: int) -> InlineKeyboardMarkup:
    """Build controls for a staged ordinal-options editor."""
    builder = KeyboardBuilder()
    if label_count:
        builder.row_buttons_tuple(
            (
                TextKey.ORDINAL_REMOVE,
                OrdinalDraftCallback(action=OrdinalDraftAction.REMOVE),
            ),
            (
                TextKey.ORDINAL_RESET,
                OrdinalDraftCallback(action=OrdinalDraftAction.RESET),
            ),
        )
    if label_count >= 2:
        builder.row_buttons_tuple(
            (
                TextKey.ORDINAL_FINISH,
                OrdinalDraftCallback(action=OrdinalDraftAction.FINISH),
            )
        )
    return builder.as_markup()

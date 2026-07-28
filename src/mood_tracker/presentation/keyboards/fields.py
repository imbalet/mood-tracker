"""Inline keyboards for field settings and creation."""

from uuid import UUID

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.application.commands import MoveDirection
from mood_tracker.domain.entities import Field
from mood_tracker.domain.enums import FieldStatus, FieldType
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldCreateCallback,
    FieldMoveCallback,
    FieldsListAction,
    FieldsListCallback,
    FieldStatusCallback,
    MenuCallback,
    MenuSection,
    OrdinalBaseCallback,
    OrdinalDraftAction,
    OrdinalDraftCallback,
    PaletteCallback,
    PalettePreset,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.utils import KeyboardBuilder


def fields_keyboard(fields: tuple[Field, ...]) -> InlineKeyboardMarkup:
    """Build a selection list for all fields visible in settings."""
    builder = KeyboardBuilder()
    for field in fields:
        builder.row_buttons_text_tuple(
            (field.name, FieldCallback(action=FieldAction.OPEN, field_id=field.id))
        )
    builder.row_buttons_tuple(
        (TextKey.ADD_FIELD, FieldsListCallback(action=FieldsListAction.CREATE))
    )
    builder.row_buttons_tuple(
        (TextKey.FIELD_REORDER, FieldsListCallback(action=FieldsListAction.ORDER))
    )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    return builder.as_markup()


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


def field_card_keyboard(field: Field) -> InlineKeyboardMarkup:
    """Build actions valid for one field's current configuration."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_RENAME,
            FieldCallback(action=FieldAction.RENAME, field_id=field.id),
        )
    )
    version_key = {
        FieldType.SCALE: TextKey.FIELD_CHANGE_RANGE,
        FieldType.ORDINAL: TextKey.FIELD_CHANGE_OPTIONS,
    }.get(field.current_version.type)
    if version_key is not None:
        builder.row_buttons_tuple(
            (
                version_key,
                FieldCallback(action=FieldAction.VERSION, field_id=field.id),
            )
        )
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_EMOJI,
            FieldCallback(action=FieldAction.EMOJI, field_id=field.id),
        ),
        (
            TextKey.FIELD_CLEAR_EMOJI,
            FieldCallback(action=FieldAction.CLEAR_EMOJI, field_id=field.id),
        ),
    )
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_TOGGLE_CALENDAR,
            FieldCallback(action=FieldAction.TOGGLE_CALENDAR, field_id=field.id),
        )
    )
    if field.is_core:
        builder.row_buttons_tuple(
            (
                TextKey.FIELD_PALETTE,
                FieldCallback(action=FieldAction.PALETTE, field_id=field.id),
            )
        )
    else:
        builder.row_buttons_text_tuple(
            *(
                (
                    TEXTS[
                        {
                            FieldStatus.ACTIVE: TextKey.FIELD_STATUS_ACTIVE,
                            FieldStatus.INACTIVE: TextKey.FIELD_STATUS_INACTIVE,
                            FieldStatus.HIDDEN: TextKey.FIELD_STATUS_HIDDEN,
                        }[status]
                    ],
                    FieldStatusCallback(field_id=field.id, status=status),
                )
                for status in FieldStatus
            )
        )
    builder.row_buttons_tuple((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
    return builder.as_markup()


def field_order_keyboard(
    fields: tuple[Field, ...], selected_id: UUID | None
) -> InlineKeyboardMarkup:
    """Build an immediately re-rendered field-order editor."""
    builder = KeyboardBuilder()
    for field in fields:
        label = (
            TEXTS[TextKey.FIELD_ORDER_SELECTED].format(name=field.name)
            if field.id == selected_id
            else field.name
        )
        builder.row_buttons_text_tuple(
            (label, FieldCallback(action=FieldAction.ORDER, field_id=field.id))
        )
    selected_index = next(
        (index for index, field in enumerate(fields) if field.id == selected_id), None
    )
    if selected_id is not None and selected_index is not None:
        move_buttons = []
        if selected_index > 0:
            move_buttons.append(
                (
                    TEXTS[TextKey.FIELD_MOVE_UP],
                    FieldMoveCallback(field_id=selected_id, direction=MoveDirection.UP),
                )
            )
        if selected_index < len(fields) - 1:
            move_buttons.append(
                (
                    TEXTS[TextKey.FIELD_MOVE_DOWN],
                    FieldMoveCallback(
                        field_id=selected_id,
                        direction=MoveDirection.DOWN,
                    ),
                )
            )
        if move_buttons:
            builder.row_buttons_text_tuple(*move_buttons)
        builder.row_buttons_tuple(
            (
                TextKey.FIELD_ORDER_DONE,
                MenuCallback(section=MenuSection.FIELDS),
            )
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
    builder.row_buttons_tuple(
        (TextKey.ORDINAL_ADD, OrdinalDraftCallback(action=OrdinalDraftAction.ADD))
    )
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


def palette_keyboard(field_id: UUID) -> InlineKeyboardMarkup:
    """Offer human-readable presets alongside the custom HEX route."""
    builder = KeyboardBuilder()
    for preset, text_key in (
        (PalettePreset.WARM, TextKey.PALETTE_WARM),
        (PalettePreset.FOREST, TextKey.PALETTE_FOREST),
        (PalettePreset.COOL, TextKey.PALETTE_COOL),
        (PalettePreset.CUSTOM, TextKey.PALETTE_CUSTOM),
    ):
        builder.row_buttons_text_tuple(
            (TEXTS[text_key], PaletteCallback(field_id=field_id, preset=preset))
        )
    builder.row_buttons_tuple(
        (TextKey.BACK, FieldCallback(action=FieldAction.OPEN, field_id=field_id))
    )
    return builder.as_markup()

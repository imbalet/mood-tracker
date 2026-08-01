"""Complete Telegram screens for field settings and palette management."""

from html import escape

from aiogram.types import (
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichMessage,
    InputRichMessageMedia,
)

from mood_tracker.application.commands import MoveDirection
from mood_tracker.domain.entities import ScaleConfig, StatePalette
from mood_tracker.domain.enums import FieldStatus, FieldType
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldMoveCallback,
    FieldsListAction,
    FieldsListCallback,
    FieldStatusCallback,
    MenuCallback,
    MenuSection,
    PaletteCallback,
    PalettePreset,
    QuestionnaireFieldAction,
    QuestionnaireFieldCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.palette_preview import render_palette_preview
from mood_tracker.presentation.screens.screen import Screen
from mood_tracker.presentation.utils.keyboard_builder import KeyboardBuilder
from mood_tracker.presentation.view_models.fields import (
    FieldCardView,
    FieldOrderView,
    FieldsListView,
    PaletteView,
)


def fields_list_screen(view: FieldsListView) -> Screen:
    """Build the settings list for every user-owned field."""
    builder = KeyboardBuilder()
    for item in view.items:
        builder.row_buttons_text_tuple(
            (
                item.name,
                FieldCallback(
                    action=FieldAction.OPEN, field_id=item.id, kind=view.kind
                ),
            )
        )
    builder.row_buttons_tuple(
        (
            TextKey.ADD_FIELD,
            FieldsListCallback(action=FieldsListAction.CREATE, kind=view.kind),
        )
    )
    builder.row_buttons_text_tuple(
        (
            "Добавить из другой анкеты",
            FieldsListCallback(action=FieldsListAction.ATTACH, kind=view.kind),
        )
    )
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_REORDER,
            FieldsListCallback(action=FieldsListAction.ORDER, kind=view.kind),
        )
    )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    text = (
        "\n\n".join((TEXTS[TextKey.FIELDS_TITLE], TEXTS[TextKey.NO_FIELDS]))
        if not view.items
        else TEXTS[TextKey.FIELDS_TITLE]
    )
    return Screen(text, builder.as_markup())


def field_card_screen(view: FieldCardView) -> Screen:
    """Build a field's display and all actions valid for its type."""
    lines = [
        TEXTS[TextKey.FIELD_DETAILS].format(name=escape(view.name)),
        f"Тип: {_field_type_label(view.type)}",
        f"Статус: <b>{_field_status_label(view.status)}</b>",
        (
            f"В анкете: {'обязательное' if view.is_required else 'необязательное'}"
            if view.kind.value == "event"
            else ""
        ),
        escape(view.semantic_text),
        f"Emoji: {escape(view.emoji or '—')}",
        f"Показывать в календаре: {'да' if view.show_in_calendar else 'нет'}",
        f"Версий значений: {view.version_count}",
        TEXTS[TextKey.FIELD_POSITION].format(position=view.position),
    ]
    if view.palette_colors is not None:
        minimum, middle, maximum = view.palette_colors
        lines.append(f"Палитра: <code>{minimum} → {middle} → {maximum}</code>")
    return Screen("\n".join(line for line in lines if line), _field_card_keyboard(view))


def field_order_screen(view: FieldOrderView) -> Screen:
    """Build the selected-field order editor with only valid move controls."""
    builder = KeyboardBuilder()
    for item in view.items:
        label = (
            TEXTS[TextKey.FIELD_ORDER_SELECTED].format(name=item.name)
            if item.is_selected
            else item.name
        )
        builder.row_buttons_text_tuple(
            (
                label,
                FieldCallback(
                    action=FieldAction.ORDER, field_id=item.id, kind=view.kind
                ),
            )
        )
    if view.selected_id is not None:
        move_buttons = []
        if view.can_move_up:
            move_buttons.append(
                (
                    TEXTS[TextKey.FIELD_MOVE_UP],
                    FieldMoveCallback(
                        field_id=view.selected_id,
                        direction=MoveDirection.UP,
                        kind=view.kind,
                    ),
                )
            )
        if view.can_move_down:
            move_buttons.append(
                (
                    TEXTS[TextKey.FIELD_MOVE_DOWN],
                    FieldMoveCallback(
                        field_id=view.selected_id,
                        direction=MoveDirection.DOWN,
                        kind=view.kind,
                    ),
                )
            )
        if move_buttons:
            builder.row_buttons_text_tuple(*move_buttons)
        builder.row_buttons_tuple(
            (TextKey.FIELD_ORDER_DONE, MenuCallback(section=MenuSection.FIELDS))
        )
    builder.row_buttons_tuple((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
    return Screen(TEXTS[TextKey.FIELD_ORDER_TITLE], builder.as_markup())


def palette_screen(view: PaletteView) -> Screen:
    """Build the numbered rich legend and direct palette-selection controls."""
    minimum, middle, maximum = view.colors
    config = ScaleConfig(view.minimum, view.maximum)
    palette = StatePalette(minimum, middle, maximum)
    content = InputRichMessage(
        html=(
            "<h3>Палитра состояния</h3>"
            '<img src="tg://photo?id=scale"/>'
            "<p><code>"
            f"{minimum} → {middle} → {maximum}"
            "</code></p>"
        ),
        media=[
            InputRichMessageMedia(
                id="scale",
                media=InputMediaPhoto(media=render_palette_preview(config, palette)),
            )
        ],
    )
    builder = KeyboardBuilder()
    for preset, text_key in (
        (PalettePreset.WARM, TextKey.PALETTE_WARM),
        (PalettePreset.FOREST, TextKey.PALETTE_FOREST),
        (PalettePreset.COOL, TextKey.PALETTE_COOL),
        (PalettePreset.CUSTOM, TextKey.PALETTE_CUSTOM),
    ):
        builder.row_buttons_text_tuple(
            (TEXTS[text_key], PaletteCallback(field_id=view.field_id, preset=preset))
        )
    builder.row_buttons_tuple(
        (
            TextKey.BACK,
            FieldCallback(action=FieldAction.OPEN, field_id=view.field_id),
        )
    )
    return Screen(content, builder.as_markup())


def _field_card_keyboard(view: FieldCardView) -> InlineKeyboardMarkup:
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_RENAME,
            FieldCallback(action=FieldAction.RENAME, field_id=view.id, kind=view.kind),
        )
    )
    version_key = {
        FieldType.SCALE: TextKey.FIELD_CHANGE_RANGE,
        FieldType.ORDINAL: TextKey.FIELD_CHANGE_OPTIONS,
    }.get(view.type)
    if version_key is not None:
        builder.row_buttons_tuple(
            (
                version_key,
                FieldCallback(
                    action=FieldAction.VERSION, field_id=view.id, kind=view.kind
                ),
            )
        )
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_EMOJI,
            FieldCallback(action=FieldAction.EMOJI, field_id=view.id, kind=view.kind),
        ),
        (
            TextKey.FIELD_CLEAR_EMOJI,
            FieldCallback(
                action=FieldAction.CLEAR_EMOJI, field_id=view.id, kind=view.kind
            ),
        ),
    )
    if view.kind.value == "day":
        builder.row_buttons_tuple(
            (
                TextKey.FIELD_TOGGLE_CALENDAR,
                FieldCallback(
                    action=FieldAction.TOGGLE_CALENDAR, field_id=view.id, kind=view.kind
                ),
            )
        )
    if view.is_core:
        builder.row_buttons_tuple(
            (
                TextKey.FIELD_PALETTE,
                FieldCallback(
                    action=FieldAction.PALETTE, field_id=view.id, kind=view.kind
                ),
            )
        )
    else:
        builder.row_buttons_text_tuple(
            *(
                (
                    TEXTS[_field_status_key(status)],
                    FieldStatusCallback(
                        field_id=view.id, status=status, kind=view.kind
                    ),
                )
                for status in FieldStatus
            )
        )
    if view.kind.value == "event":
        builder.row_buttons_text_tuple(
            (
                "Сделать необязательным"
                if view.is_required
                else "Сделать обязательным",
                QuestionnaireFieldCallback(
                    action=QuestionnaireFieldAction.TOGGLE_REQUIRED,
                    field_id=view.id,
                    kind=view.kind,
                ),
            )
        )
    if view.can_detach:
        builder.row_buttons_text_tuple(
            (
                "Убрать из анкеты",
                QuestionnaireFieldCallback(
                    action=QuestionnaireFieldAction.DETACH,
                    field_id=view.id,
                    kind=view.kind,
                ),
            )
        )
    builder.row_buttons_tuple((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
    return builder.as_markup()


def _field_status_key(status: FieldStatus) -> TextKey:
    return {
        FieldStatus.ACTIVE: TextKey.FIELD_STATUS_ACTIVE,
        FieldStatus.INACTIVE: TextKey.FIELD_STATUS_INACTIVE,
        FieldStatus.HIDDEN: TextKey.FIELD_STATUS_HIDDEN,
    }[status]


def _field_status_label(status: FieldStatus) -> str:
    return TEXTS[_field_status_key(status)]


def _field_type_label(type: FieldType) -> str:
    return TEXTS[
        {
            FieldType.SCALE: TextKey.FIELD_TYPE_SCALE,
            FieldType.ORDINAL: TextKey.FIELD_TYPE_ORDINAL,
            FieldType.TEXT: TextKey.FIELD_TYPE_TEXT,
        }[type]
    ]

"""Complete Telegram screens for filling one daily entry."""

from html import escape

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    EventAction,
    EventCallback,
    MenuCallback,
    MenuSection,
    OpenDayCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens.screen import Screen
from mood_tracker.presentation.utils.keyboard_builder import KeyboardBuilder
from mood_tracker.presentation.view_models import (
    DayCardView,
    DayFieldAction,
    DayPromptKind,
    DayValuePromptView,
    ReferenceReviewView,
)


def day_card_screen(view: DayCardView) -> Screen:
    """Build the editable overview of one calendar day."""
    return Screen(_card_text(view), _card_keyboard(view))


def day_value_prompt_screen(
    view: DayValuePromptView, *, error: str | None = None
) -> Screen:
    """Build a value prompt while retaining the day context above it."""
    prompt = (
        TEXTS[TextKey.ENTER_TEXT].format(name=escape(view.field_name))
        if view.kind is DayPromptKind.TEXT
        else TEXTS[TextKey.SELECT_VALUE].format(name=escape(view.field_name))
    )
    parts = [_card_text(view.card), error, prompt]
    return Screen(
        "\n\n".join(part for part in parts if part),
        _value_prompt_keyboard(view),
    )


def reference_review_screen(view: ReferenceReviewView) -> Screen:
    """Build the boundary-value confirmation prompt."""
    adjective = "лучше" if view.type.value == "best" else "хуже"
    builder = KeyboardBuilder()
    builder.row_buttons_text_tuple(
        *(
            (
                label,
                ReferenceCallback(
                    day_id=view.day_id,
                    type=view.type,
                    is_new_record=is_new_record,
                ),
            )
            for is_new_record, label in (
                (True, TEXTS[TextKey.YES]),
                (False, TEXTS[TextKey.NO]),
            )
        )
    )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    return Screen(
        TEXTS[TextKey.REFERENCE_QUESTION].format(adjective=adjective),
        builder.as_markup(),
    )


def _card_text(view: DayCardView) -> str:
    status = TextKey.DAY_COMPLETE if view.is_complete else TextKey.DAY_DRAFT
    lines = [f"<b>{view.date_label}</b> · {TEXTS[status]}"]
    if not view.entries:
        lines.append(TEXTS[TextKey.EMPTY_DAY])
        return "\n\n".join(lines)
    for entry in view.entries:
        emoji = f"{entry.emoji} " if entry.emoji else ""
        value = (
            TEXTS[TextKey.DAY_SKIPPED]
            if entry.is_skipped
            else escape(entry.rendered_value or "")
        )
        lines.append(f"{emoji}<b>{escape(entry.name)}</b>: {value}")
    return "\n".join(lines)


def _card_keyboard(view: DayCardView) -> InlineKeyboardMarkup:
    builder = KeyboardBuilder()
    for action in view.actions:
        text = TEXTS[
            TextKey.EDIT_FIELD
            if action.action is DayFieldAction.EDIT
            else TextKey.ADD_FIELD_VALUE
        ].format(name=action.name)
        builder.row_buttons_text_tuple(
            (
                text,
                EditDayValueCallback(day=view.day, field_id=action.field_id),
            )
        )
    for item in view.events:
        builder.row_buttons_text_tuple(
            (
                item.label,
                EventCallback(action=EventAction.OPEN, event_id=item.event_id),
            )
        )
    builder.row_buttons_text_tuple(
        (
            "＋ Добавить событие",
            EventCallback(action=EventAction.START, day=view.day),
        )
    )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    return builder.as_markup()


def _value_prompt_keyboard(view: DayValuePromptView) -> InlineKeyboardMarkup:
    builder = KeyboardBuilder(row_width=4)
    if view.kind is DayPromptKind.CHOICES:
        builder.buttons_text_tuple(
            *(
                (
                    option.label,
                    DayValueCallback(
                        day=view.card.day,
                        field_id=view.field_id,
                        value=option.value,
                    ),
                )
                for option in view.options
            )
        )
    else:
        builder.row_buttons_tuple(
            (
                TextKey.SKIP,
                SkipTextCallback(day=view.card.day, field_id=view.field_id),
            )
        )
    builder.row_buttons_tuple((TextKey.BACK_TO_DAY, OpenDayCallback(day=view.card.day)))
    return builder.as_markup()

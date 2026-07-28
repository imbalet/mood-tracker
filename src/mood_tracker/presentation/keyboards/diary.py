"""Inline keyboards used by the daily questionnaire."""

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from mood_tracker.application.commands import DayForm, ReferenceReview
from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import FieldStatus
from mood_tracker.presentation.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.utils import KeyboardBuilder


def field_value_keyboard(field: Field, day_date: date) -> InlineKeyboardMarkup:
    """Build answer buttons appropriate for a field's current version."""
    builder = KeyboardBuilder()
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        for value in range(config.minimum, config.maximum + 1):
            builder.button(
                text=str(value),
                callback_data=DayValueCallback(
                    day=day_date.strftime("%Y%m%d"), field_id=field.id, value=value
                ),
            )
        builder.adjust(4)
    elif isinstance(config, OrdinalConfig):
        for option in config.options:
            builder.button(
                text=option.label,
                callback_data=DayValueCallback(
                    day=day_date.strftime("%Y%m%d"),
                    field_id=field.id,
                    value=option.value,
                ),
            )
        builder.adjust(1)
    else:
        builder.button(
            text="Пропустить",
            callback_data=SkipTextCallback(
                day=day_date.strftime("%Y%m%d"), field_id=field.id
            ),
        )
    return builder.as_markup()


def reference_keyboard(review: ReferenceReview) -> InlineKeyboardMarkup:
    """Build yes/no buttons for a candidate personal record."""
    builder = KeyboardBuilder()
    for is_new_record, label in ((True, "Да"), (False, "Нет")):
        builder.button(
            text=label,
            callback_data=ReferenceCallback(
                day_id=review.day_id, type=review.type, is_new_record=is_new_record
            ),
        )
    builder.adjust(2)
    return builder.as_markup()


def day_edit_keyboard(form: DayForm) -> InlineKeyboardMarkup | None:
    """Build edit actions for visible values on a completed day."""
    if form.day is None:
        return None
    buttons = [
        InlineKeyboardButton(
            text=f"Изменить: {field.name}",
            callback_data=EditDayValueCallback(
                day=form.day_date.strftime("%Y%m%d"), field_id=field.id
            ).pack(),
        )
        for field in form.fields
        if field.status is not FieldStatus.HIDDEN and field.id in form.day.values
    ]
    return (
        InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons])
        if buttons
        else None
    )

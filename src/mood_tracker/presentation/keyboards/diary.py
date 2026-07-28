"""Inline keyboards used by the daily questionnaire."""

from datetime import date

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.application.commands import DayForm, ReferenceReview
from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import FieldStatus
from mood_tracker.presentation.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    MenuCallback,
    MenuSection,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
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
    else:
        builder.button(
            text=TEXTS[TextKey.SKIP],
            callback_data=SkipTextCallback(
                day=day_date.strftime("%Y%m%d"), field_id=field.id
            ),
        )
    builder.button(
        text=TEXTS[TextKey.BACK_TO_MENU],
        callback_data=MenuCallback(section=MenuSection.HOME),
    )
    if isinstance(config, ScaleConfig):
        builder.adjust(4, 1)
    else:
        option_count = len(config.options) if isinstance(config, OrdinalConfig) else 1
        builder.adjust(*([1] * (option_count + 1)))
    return builder.as_markup()


def reference_keyboard(review: ReferenceReview) -> InlineKeyboardMarkup:
    """Build yes/no buttons for a candidate personal record."""
    builder = KeyboardBuilder()
    for is_new_record, label in (
        (True, TEXTS[TextKey.YES]),
        (False, TEXTS[TextKey.NO]),
    ):
        builder.button(
            text=label,
            callback_data=ReferenceCallback(
                day_id=review.day_id, type=review.type, is_new_record=is_new_record
            ),
        )
    builder.adjust(2)
    builder.button(
        text=TEXTS[TextKey.BACK_TO_MENU],
        callback_data=MenuCallback(section=MenuSection.HOME),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def day_edit_keyboard(form: DayForm) -> InlineKeyboardMarkup:
    """Build edit actions for visible values on a completed day."""
    builder = KeyboardBuilder()
    if form.day is not None:
        for field in form.fields:
            if field.status is FieldStatus.HIDDEN or field.id not in form.day.values:
                continue
            builder.button(
                text=TEXTS[TextKey.EDIT_FIELD].format(name=field.name),
                callback_data=EditDayValueCallback(
                    day=form.day_date.strftime("%Y%m%d"), field_id=field.id
                ),
            )
    builder.button(
        text=TEXTS[TextKey.BACK_TO_MENU],
        callback_data=MenuCallback(section=MenuSection.HOME),
    )
    return builder.as_markup()

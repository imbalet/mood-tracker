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
    OpenDayCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.utils import KeyboardBuilder


def field_value_keyboard(field: Field, day_date: date) -> InlineKeyboardMarkup:
    """Build answer buttons appropriate for a field's current version."""
    builder = KeyboardBuilder(row_width=4)
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        builder.buttons_text_tuple(
            *(
                (
                    str(value),
                    DayValueCallback(
                        day=day_date.strftime("%Y%m%d"),
                        field_id=field.id,
                        value=value,
                    ),
                )
                for value in range(config.minimum, config.maximum + 1)
            )
        )
    elif isinstance(config, OrdinalConfig):
        for option in config.options:
            builder.row_buttons_text_tuple(
                (
                    option.label,
                    DayValueCallback(
                        day=day_date.strftime("%Y%m%d"),
                        field_id=field.id,
                        value=option.value,
                    ),
                )
            )
    else:
        builder.row_buttons_tuple(
            (
                TextKey.SKIP,
                SkipTextCallback(day=day_date.strftime("%Y%m%d"), field_id=field.id),
            )
        )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_DAY, OpenDayCallback(day=day_date.strftime("%Y%m%d")))
    )
    return builder.as_markup()


def reference_keyboard(review: ReferenceReview) -> InlineKeyboardMarkup:
    """Build yes/no buttons for a candidate personal record."""
    builder = KeyboardBuilder()
    builder.row_buttons_text_tuple(
        *(
            (
                label,
                ReferenceCallback(
                    day_id=review.day_id,
                    type=review.type,
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
    return builder.as_markup()


def day_edit_keyboard(form: DayForm) -> InlineKeyboardMarkup:
    """Build add and edit actions around the currently visible day summary."""
    builder = KeyboardBuilder()
    for field in form.fields:
        if field.status is FieldStatus.HIDDEN:
            continue
        is_completed = form.day is not None and form.day.has_completed_step(field.id)
        if is_completed:
            text = TEXTS[TextKey.EDIT_FIELD].format(name=field.name)
        elif field.status is FieldStatus.ACTIVE:
            text = TEXTS[TextKey.ADD_FIELD_VALUE].format(name=field.name)
        else:
            continue
        builder.row_buttons_text_tuple(
            (
                text,
                EditDayValueCallback(
                    day=form.day_date.strftime("%Y%m%d"), field_id=field.id
                ),
            )
        )
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    return builder.as_markup()

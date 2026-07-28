"""Typed compact callback payloads for diary interactions."""

from uuid import UUID

from aiogram.filters.callback_data import CallbackData

from mood_tracker.domain.enums import ReferenceType


class TimezoneCallback(CallbackData, prefix="timezone"):
    """Choose a predefined timezone or the manual-input path."""

    timezone: str


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

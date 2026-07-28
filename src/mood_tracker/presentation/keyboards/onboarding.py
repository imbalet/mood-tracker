"""Inline keyboards used while creating a profile."""

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks import TimezoneCallback
from mood_tracker.presentation.utils import KeyboardBuilder

TIMEZONES = (
    "Europe/Kaliningrad",
    "Europe/Moscow",
    "Europe/Samara",
    "Asia/Yekaterinburg",
    "Asia/Omsk",
    "Asia/Krasnoyarsk",
    "Asia/Irkutsk",
    "Asia/Yakutsk",
    "Asia/Vladivostok",
    "Asia/Magadan",
    "Asia/Kamchatka",
)


def timezone_keyboard() -> InlineKeyboardMarkup:
    """Build buttons for common Russian timezones and manual input."""
    builder = KeyboardBuilder()
    for timezone in TIMEZONES:
        builder.button(
            text=timezone.replace("Europe/", "").replace("Asia/", ""),
            callback_data=TimezoneCallback(timezone=timezone),
        )
    builder.button(
        text="Другой часовой пояс", callback_data=TimezoneCallback(timezone="other")
    )
    builder.adjust(2, 2, 2, 2, 2, 1, 1)
    return builder.as_markup()

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
    builder.buttons_text_tuple(
        *(
            (
                timezone.replace("Europe/", "").replace("Asia/", ""),
                TimezoneCallback(timezone=timezone),
            )
            for timezone in TIMEZONES
        )
    )
    builder.row_buttons_text_tuple(
        ("Другой часовой пояс", TimezoneCallback(timezone="other"))
    )
    return builder.as_markup()

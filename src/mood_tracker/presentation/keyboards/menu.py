"""Inline keyboards for the persistent top-level menu."""

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.utils import KeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the current minimal main menu."""
    builder = KeyboardBuilder()
    builder.button(
        text=TEXTS[TextKey.MENU_TODAY],
        callback_data=MenuCallback(section=MenuSection.TODAY),
    )
    return builder.as_markup()


def menu_button_keyboard() -> InlineKeyboardMarkup:
    """Build a single action returning to the main menu."""
    builder = KeyboardBuilder()
    builder.button(
        text=TEXTS[TextKey.BACK_TO_MENU],
        callback_data=MenuCallback(section=MenuSection.HOME),
    )
    return builder.as_markup()

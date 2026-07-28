"""Inline keyboards for the persistent top-level menu."""

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.constants import TextKey
from mood_tracker.presentation.utils import KeyboardBuilder


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the current top-level menu."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (TextKey.MENU_TODAY, MenuCallback(section=MenuSection.TODAY))
    )
    builder.row_buttons_tuple(
        (TextKey.MENU_FIELDS, MenuCallback(section=MenuSection.FIELDS))
    )
    return builder.as_markup()


def menu_button_keyboard() -> InlineKeyboardMarkup:
    """Build a single action returning to the main menu."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME))
    )
    return builder.as_markup()

"""The central inline-navigation screen."""

from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.keyboards import main_menu_keyboard
from mood_tracker.presentation.screens.screen import Screen


def main_menu_screen(*, notice: str | None = None) -> Screen:
    """Build the persistent entry screen with an optional preceding notice."""
    text = "\n\n".join(part for part in (notice, TEXTS[TextKey.MENU_TITLE]) if part)
    return Screen(text, main_menu_keyboard())

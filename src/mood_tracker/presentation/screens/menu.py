from dataclasses import dataclass
from typing import ClassVar, override

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks.callbacks import (
    MenuCallback,
    MenuSection,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens.screen import Screen


@dataclass
class MainMenuScreen(Screen):
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 1
    text: ClassVar[str | None] = TEXTS[TextKey.MENU_TITLE]

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        return (
            self._kbuilder.row(
                (TextKey.MENU_TODAY, MenuCallback(section=MenuSection.TODAY))
            )
            .row((TextKey.MENU_DATES, MenuCallback(section=MenuSection.DATES)))
            .row((TextKey.MENU_CALENDAR, MenuCallback(section=MenuSection.CALENDAR)))
            .row((TextKey.MENU_FIELDS, MenuCallback(section=MenuSection.FIELDS)))
            .as_markup()
        )

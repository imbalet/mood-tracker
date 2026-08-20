from dataclasses import dataclass
from typing import ClassVar, override

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.presentation.callbacks.callbacks import TimezoneCallback
from mood_tracker.presentation.constants import TEXTS, TIMEZONES, TextKey
from mood_tracker.presentation.screens.screen import Screen, ScreenContent


@dataclass
class SelectTimezoneScreen(Screen):
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 3
    text: ClassVar[str | None] = TEXTS[TextKey.SELECT_TIMEZONE]

    # TODO: make separate screens for onboarding and timezone selection
    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        return (
            self._kbuilder.buttons_iterable(
                (name, TimezoneCallback(timezone=tz)) for name, tz in TIMEZONES.items()
            )
            .row((TEXTS[TextKey.ANOTHER_TIMEZONE], TimezoneCallback(timezone="other")))
            .as_markup()
        )


@dataclass
class EnterTimezoneTextScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.ENTER_TIMEZONE]


@dataclass
class InvalidTimezoneScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.INVALID_TIMEZONE]


@dataclass
class TimezoneSavedScreen(Screen):
    timezone: str

    @override
    def _text(self) -> ScreenContent:
        return TEXTS[TextKey.TIMEZONE_SAVED].format(timezone=self.timezone)

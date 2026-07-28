"""Composable typed factory for Telegram inline keyboards."""

from typing import Any, Self

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from mood_tracker.presentation.constants import TEXTS, TextKey


class InlineKeyboardFactory:
    """Accumulate typed buttons while retaining explicit row control."""

    def __init__(self, row_width: int = 2) -> None:
        if row_width < 1:
            msg = "row_width must be positive"
            raise ValueError(msg)
        self._keyboard: list[list[InlineKeyboardButton]] = []
        self._current_row: list[InlineKeyboardButton] = []
        self._row_width = row_width

    def _flush_row(self) -> Self:
        """Append the current row when it contains at least one button."""
        if self._current_row:
            self._keyboard.append(self._current_row)
            self._current_row = []
        return self

    def buttons_tuple(self, *buttons: tuple[TextKey, CallbackData]) -> Self:
        """Append translated callback buttons to the current rows."""
        for text, callback_data in buttons:
            self.button(text, callback_data)
        return self

    def buttons_text_tuple(self, *buttons: tuple[str, CallbackData]) -> Self:
        """Append literal-text callback buttons to the current rows."""
        for text, callback_data in buttons:
            self.button_text(text, callback_data)
        return self

    def buttons(self, *buttons: InlineKeyboardButton) -> Self:
        """Append already-constructed buttons using the configured row width."""
        for button in buttons:
            self._current_row.append(button)
            if len(self._current_row) >= self._row_width:
                self._flush_row()
        return self

    def button(self, text: TextKey, callback_data: CallbackData, **kwargs: Any) -> Self:
        """Append a callback button using a translated static text key."""
        return self.button_text(TEXTS[text], callback_data, **kwargs)

    def button_text(
        self, text: str, callback_data: CallbackData, **kwargs: Any
    ) -> Self:
        """Append one literal-text callback button to the current row."""
        return self.buttons(
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data.pack(),
                **kwargs,
            )
        )

    def row_buttons(self, *buttons: InlineKeyboardButton) -> Self:
        """Finish the current row and append one explicit row of buttons."""
        self._flush_row()
        if buttons:
            self._keyboard.append(list(buttons))
        return self

    def row_buttons_tuple(self, *buttons: tuple[TextKey, CallbackData]) -> Self:
        """Finish the current row and append translated callback buttons."""
        return self.row_buttons(
            *(
                InlineKeyboardButton(text=TEXTS[text], callback_data=callback.pack())
                for text, callback in buttons
            )
        )

    def row_buttons_text_tuple(self, *buttons: tuple[str, CallbackData]) -> Self:
        """Finish the current row and append literal-text callback buttons."""
        return self.row_buttons(
            *(
                InlineKeyboardButton(text=text, callback_data=callback.pack())
                for text, callback in buttons
            )
        )

    def as_markup(self) -> InlineKeyboardMarkup:
        """Return a Telegram keyboard, flushing any incomplete final row."""
        self._flush_row()
        return InlineKeyboardMarkup(inline_keyboard=self._keyboard)


class KeyboardBuilder(InlineKeyboardFactory):
    """Project-level name for the reusable inline keyboard factory."""

    pass

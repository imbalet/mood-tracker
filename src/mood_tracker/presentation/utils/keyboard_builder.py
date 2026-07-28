"""Small reusable builder for typed aiogram callback buttons."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class KeyboardBuilder:
    """Build inline keyboards without exposing callback serialization to callers."""

    def __init__(self) -> None:
        self._builder = InlineKeyboardBuilder()

    def button(self, text: str, callback_data: CallbackData) -> None:
        """Append one typed callback button."""
        self._builder.button(text=text, callback_data=callback_data)

    def adjust(self, *sizes: int) -> None:
        """Set row widths for accumulated buttons."""
        self._builder.adjust(*sizes)

    def as_markup(self) -> InlineKeyboardMarkup:
        """Return the final Telegram keyboard."""
        return self._builder.as_markup()

"""A complete Telegram screen ready for delivery."""

from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup, InputRichMessage

ScreenContent = str | InputRichMessage


@dataclass(frozen=True, slots=True)
class Screen:
    """Pair one screen's content with its inline controls."""

    content: ScreenContent
    reply_markup: InlineKeyboardMarkup | None = None

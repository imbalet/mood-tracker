"""Narrowed aiogram callback type after middleware validation."""

from aiogram.types import CallbackQuery, Message


class CallbackQueryWithMessage(CallbackQuery):
    """Callback query whose source message is accessible."""

    message: Message  # pyright: ignore[reportGeneralTypeIssues]

"""Resilient Telegram message delivery shared by presentation handlers."""

import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup, InputRichMessage, Message

logger = logging.getLogger(__name__)


class Sender:
    """Handle Telegram API failures for outgoing messages."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def answer(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | None:
        """Send a reply while applying Telegram error handling."""
        return await self._send(message.chat.id, text, reply_markup)

    async def answer_rich(
        self,
        message: Message,
        rich_message: InputRichMessage,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | None:
        """Send a structured rich message with optional interactive controls."""
        try:
            return await self._bot.send_rich_message(
                chat_id=message.chat.id,
                rich_message=rich_message,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest, TelegramForbiddenError:
            logger.exception(
                "Telegram rejected rich message for chat %s", message.chat.id
            )
            return None

    async def edit(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool | None:
        """Edit an existing bot message, returning None when it cannot be changed."""
        return await self.edit_by_id(
            message.chat.id, message.message_id, text, reply_markup
        )

    async def edit_by_id(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool | None:
        """Edit a known interactive message in one chat."""
        try:
            return await self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest:
            return None

    async def edit_rich_by_id(
        self,
        chat_id: int,
        message_id: int,
        rich_message: InputRichMessage,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool | None:
        """Replace the content of a known message with a rich message."""
        try:
            return await self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                rich_message=rich_message,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest:
            return None

    async def delete(self, message: Message) -> None:
        """Remove a user message after its content has been processed."""
        await self.delete_by_id(message.chat.id, message.message_id)

    async def delete_by_id(self, chat_id: int, message_id: int) -> None:
        """Remove a message when the bot is allowed to do so."""
        try:
            await self._bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            return

    async def _send(
        self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None
    ) -> Message | None:
        for _ in range(3):
            try:
                return await self._bot.send_message(
                    chat_id, text, reply_markup=reply_markup
                )
            except TelegramRetryAfter as error:
                logger.warning(
                    "Telegram flood wait for chat %s: %s", chat_id, error.retry_after
                )
                return None
            except TelegramForbiddenError:
                logger.info("Bot is blocked by chat %s", chat_id)
                return None
            except TelegramBadRequest:
                logger.exception("Telegram rejected message for chat %s", chat_id)
                return None
        return None

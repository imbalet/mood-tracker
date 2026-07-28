"""Presentation-wide dependency injection and callback guards."""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InaccessibleMessage, TelegramObject, Update

from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.sender import Sender
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.utils import update_main_message


class ApplicationMiddleware(BaseMiddleware):
    """Inject the authenticated Telegram ID and use-case factory into handlers."""

    def __init__(self, services: ApplicationServices, sender: Sender) -> None:
        self._services = services
        self._sender = sender

    async def __call__[ResultT](
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[ResultT]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> ResultT | None:
        if not isinstance(event, Update):
            return None
        if event.message is not None and event.message.from_user is not None:
            telegram_id = event.message.from_user.id
        elif event.callback_query is not None:
            telegram_id = event.callback_query.from_user.id
        else:
            return None
        data["telegram_id"] = telegram_id
        data["services"] = self._services
        data["update_main_message"] = partial(update_main_message, self._sender)
        return await handler(event, data)


class CallbackMessageMiddleware(BaseMiddleware):
    """Reject callbacks whose source message is no longer accessible."""

    async def __call__[ResultT](
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[ResultT]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> ResultT | None:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        if event.message is None or isinstance(event.message, InaccessibleMessage):
            await event.answer("Сообщение недоступно.", show_alert=True)
            return None
        return await handler(cast(CallbackQueryWithMessage, event), data)

"""Presentation-wide dependency injection and callback guards."""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any, cast, override

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InaccessibleMessage, TelegramObject, Update

from mood_tracker.presentation.rendering.calendar import MonthCalendarImageService
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import update_main_message
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.utils.sender import Sender


class ApplicationMiddleware(BaseMiddleware):
    """Inject the authenticated Telegram ID and use-case factory into handlers."""

    def __init__(
        self,
        services: ApplicationServices,
        sender: Sender,
        calendar_images: MonthCalendarImageService,
    ) -> None:
        self._services = services
        self._sender = sender
        self._calendar_images = calendar_images

    @override
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
        data["calendar_images"] = self._calendar_images
        data["presentation_data"] = PresentationData(data["state"])
        data["update_main_message"] = partial(update_main_message, self._sender)
        return await handler(event, data)


class CallbackMessageMiddleware(BaseMiddleware):
    """Reject callbacks whose source message is no longer accessible."""

    @override
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

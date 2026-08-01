"""Aiogram application entry point and dependency composition root."""

from __future__ import annotations

import asyncio
import contextlib

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram.methods import DeleteWebhook
from aiogram.types import BotCommand

from mood_tracker.application.errors import ApplicationError
from mood_tracker.config import get_settings
from mood_tracker.healthcheck import start_healthcheck_server
from mood_tracker.infrastructure.db.session import create_session_factory
from mood_tracker.logger import setup_logging
from mood_tracker.presentation.error_handler import (
    handle_application_error,
    handle_stale_callback,
    handle_unexpected_error,
)
from mood_tracker.presentation.errors import StaleCallback
from mood_tracker.presentation.handlers import (
    calendar_router,
    events_router,
    fields_router,
    menu_router,
    onboarding_router,
    today_router,
)
from mood_tracker.presentation.middleware import (
    ApplicationMiddleware,
    CallbackMessageMiddleware,
)
from mood_tracker.presentation.rendering.calendar import MonthCalendarImageService
from mood_tracker.presentation.sender import Sender
from mood_tracker.presentation.services import ApplicationServices


async def run() -> None:
    """Start the Telegram transport lifecycle.

    Feature routers and application dependencies are composed here in later core
    iterations. Domain and application packages remain independent from aiogram.
    """
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    dispatcher = Dispatcher()
    dispatcher.errors.register(
        handle_stale_callback, ExceptionTypeFilter(StaleCallback)
    )
    dispatcher.errors.register(
        handle_application_error, ExceptionTypeFilter(ApplicationError)
    )
    dispatcher.errors.register(handle_unexpected_error, ExceptionTypeFilter(Exception))
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    engine, session_factory = create_session_factory(settings.DB_URL)
    services = ApplicationServices(session_factory)
    calendar_images = MonthCalendarImageService()
    dispatcher.include_routers(
        menu_router,
        onboarding_router,
        today_router,
        events_router,
        calendar_router,
        fields_router,
    )
    dispatcher.update.middleware(
        ApplicationMiddleware(services, Sender(bot), calendar_images)
    )
    dispatcher.callback_query.middleware(CallbackMessageMiddleware())
    health_task = asyncio.create_task(
        start_healthcheck_server(settings.HEALTHCHECK_PORT)
    )

    try:
        await bot(DeleteWebhook(drop_pending_updates=True))
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть дневник"),
                BotCommand(command="menu", description="Открыть меню"),
                BotCommand(command="today", description="Заполнить сегодняшний день"),
                BotCommand(command="event", description="Быстро записать событие"),
                BotCommand(command="dates", description="Выбрать дату"),
                BotCommand(command="calendar", description="Календарь месяца"),
            ]
        )
        await dispatcher.start_polling(bot)
    finally:
        health_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await health_task
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    """Run the Telegram bot."""
    asyncio.run(run())


if __name__ == "__main__":
    main()

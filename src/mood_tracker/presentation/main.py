"""Aiogram application entry point and dependency composition root."""

from __future__ import annotations

import asyncio
import contextlib

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.methods import DeleteWebhook

from mood_tracker.config import get_settings
from mood_tracker.healthcheck import start_healthcheck_server
from mood_tracker.infrastructure.db.session import create_session_factory
from mood_tracker.logger import setup_logging
from mood_tracker.presentation.handlers import onboarding_router, today_router
from mood_tracker.presentation.middleware import (
    ApplicationMiddleware,
    CallbackMessageMiddleware,
)
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
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    engine, session_factory = create_session_factory(settings.DB_URL)
    services = ApplicationServices(session_factory)
    dispatcher.include_routers(onboarding_router, today_router)
    dispatcher.update.middleware(ApplicationMiddleware(services, Sender(bot)))
    dispatcher.callback_query.middleware(CallbackMessageMiddleware())
    health_task = asyncio.create_task(
        start_healthcheck_server(settings.HEALTHCHECK_PORT)
    )

    try:
        await bot(DeleteWebhook(drop_pending_updates=True))
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

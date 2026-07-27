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
from mood_tracker.logger import setup_logging


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


def main() -> None:
    """Run the Telegram bot."""
    asyncio.run(run())


if __name__ == "__main__":
    main()

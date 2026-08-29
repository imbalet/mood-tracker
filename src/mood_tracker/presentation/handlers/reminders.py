"""Telegram command for enabling and disabling daily reminders."""

from datetime import time, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from mood_tracker.application.contracts.users import (
    GetUserByTelegramId,
    SetReminderSettings,
)
from mood_tracker.presentation.services import ApplicationServices

# TODO: посмотреть слоп

router = Router(name="reminders")


@router.message(Command("reminders"))
async def reminders(
    message: Message, telegram_id: int, services: ApplicationServices
) -> None:
    """Configure reminders with ``/reminders on [HH:MM]`` or ``off``."""
    profile = await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )
    if profile is None:
        await message.answer("Сначала открой бота командой /start.")
        return

    args = (message.text or "").split()[1:]
    if not args or args[0].lower() not in {"on", "off"}:
        await message.answer("Использование: /reminders on 20:00 или /reminders off")
        return
    enabled = args[0].lower() == "on"
    reminder_time = time(20)
    if len(args) > 1:
        try:
            reminder_time = time.fromisoformat(args[1])
        except ValueError:
            await message.answer("Время укажи в формате ЧЧ:ММ, например 20:00.")
            return

    await services.set_reminder_settings().execute(
        SetReminderSettings(
            user_id=profile.id,
            is_enabled=enabled,
            reminder_time=reminder_time,
            repeat_interval=timedelta(days=1),
            max_reminders_per_day=1,
        )
    )
    if enabled:
        await message.answer(
            f"Напоминания включены. Каждый день в {reminder_time:%H:%M} "
            f"({profile.timezone.name})."
        )
    else:
        await message.answer("Напоминания выключены.")

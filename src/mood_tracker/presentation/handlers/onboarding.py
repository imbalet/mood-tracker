"""Handlers for creating a profile and choosing its timezone."""

from typing import cast

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from mood_tracker.application.contracts.users import GetUserByTelegramId, RegisterUser
from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.value_objects import UserTimezone
from mood_tracker.presentation.callbacks.callbacks import (
    MenuCallback,
    MenuSection,
    TimezoneCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens.menu import MainMenuScreen
from mood_tracker.presentation.screens.timezone import (
    EnterTimezoneTextScreen,
    InvalidTimezoneScreen,
    SelectTimezoneScreen,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import Onboarding, PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage

router = Router(name="onboarding")


@router.callback_query(MenuCallback.filter(F.section == MenuSection.HOME))
@router.message(Command("menu"))
@router.message(CommandStart())
async def start(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Start timezone selection for a new profile."""
    command = GetUserByTelegramId(telegram_id=telegram_id)
    profile = await services.get_user_by_telegram_id().execute(command)
    if profile is not None:
        await state.set_state(None)
        await presentation_data.clear_flow()
        await update_main_message(MainMenuScreen(), create_new=True)
        return
    await state.set_state(Onboarding.waiting_timezone)
    await update_main_message(
        content=SelectTimezoneScreen(notice=TextKey.ONBOARDING_GREETING),
        create_new=True,
    )


@router.callback_query(TimezoneCallback.filter())
@router.message(Onboarding.waiting_timezone, F.text)
async def choose_timezone(
    event: Message | CallbackQueryWithMessage,
    *,
    callback_data: TimezoneCallback | None = None,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    if isinstance(event, CallbackQuery) and callback_data:
        if callback_data.timezone == "other":
            await state.set_state(Onboarding.waiting_timezone)
            await update_main_message(EnterTimezoneTextScreen())
            return
        timezone_name = callback_data.timezone
    else:
        event = cast(Message, event)
        timezone_name = str(event.text).strip()

    try:
        timezone = UserTimezone(timezone_name)
    except InvalidTimezone:
        # TODO: move to exception handlers
        await update_main_message(
            InvalidTimezoneScreen(),
        )
        return

    profile = await services.register_user().execute(
        RegisterUser(telegram_id, timezone)
    )
    await state.set_state(None)
    await presentation_data.clear_flow()
    await update_main_message(
        MainMenuScreen(
            notice=TEXTS[TextKey.TIMEZONE_SAVED].format(timezone=profile.timezone.name)
        ),
    )

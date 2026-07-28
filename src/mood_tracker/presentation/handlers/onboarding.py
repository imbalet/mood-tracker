"""Handlers for creating a profile and choosing its timezone."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import GetUserByTelegramId, RegisterUser
from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.value_objects import UserTimezone
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import TimezoneCallback
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.handlers.menu import render_menu
from mood_tracker.presentation.keyboards import main_menu_keyboard, timezone_keyboard
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.states import Onboarding
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="onboarding")


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Start timezone selection for a new profile."""
    profile = await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )
    if profile is not None:
        await state.clear()
        await render_menu(state, message, update_main_message, create_new=True)
        return
    await state.set_state(Onboarding.waiting_timezone)
    await update_main_message(
        state,
        message,
        TEXTS[TextKey.ONBOARDING_GREETING],
        reply_markup=timezone_keyboard(),
        create_new=True,
    )


@router.callback_query(TimezoneCallback.filter())
async def choose_timezone(
    query: CallbackQueryWithMessage,
    callback_data: TimezoneCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Handle a predefined timezone or request manual IANA input."""
    if callback_data.timezone == "other":
        await state.set_state(Onboarding.waiting_timezone)
        await update_main_message(
            state,
            query,
            TEXTS[TextKey.ENTER_TIMEZONE],
        )
        return
    await _register(
        state, query, telegram_id, callback_data.timezone, services, update_main_message
    )


@router.message(Onboarding.waiting_timezone, F.text)
async def choose_timezone_text(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Accept a manually entered IANA timezone."""
    await _register(
        state, message, telegram_id, message.text or "", services, update_main_message
    )


async def _register(
    state: FSMContext,
    event: Message | CallbackQueryWithMessage,
    telegram_id: int,
    timezone_name: str,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    try:
        timezone = UserTimezone(timezone_name)
    except InvalidTimezone:
        await update_main_message(
            state,
            event,
            TEXTS[TextKey.INVALID_TIMEZONE],
        )
        return
    profile = await services.register_user().execute(
        RegisterUser(telegram_id, timezone)
    )
    await state.clear()
    await update_main_message(
        state,
        event,
        "\n\n".join(
            (
                TEXTS[TextKey.TIMEZONE_SAVED].format(timezone=profile.timezone.name),
                TEXTS[TextKey.MENU_TITLE],
            )
        ),
        reply_markup=main_menu_keyboard(),
    )

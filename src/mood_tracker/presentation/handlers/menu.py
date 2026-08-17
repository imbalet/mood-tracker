"""Handlers for the persistent inline home screen."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.presentation.callbacks.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.screens import main_menu_screen
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage

router = Router(name="menu")


@router.message(Command("menu"))
async def open_menu(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the menu when a profile already exists."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await update_main_message(
        presentation_data, message, main_menu_screen(), create_new=True
    )


@router.callback_query(MenuCallback.filter(F.section == MenuSection.HOME))
async def return_to_menu(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Discard transient input and return to the main screen."""
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await update_main_message(
        presentation_data,
        query,
        main_menu_screen(),
    )

"""Handlers for the persistent inline home screen."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import GetUserByTelegramId
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.keyboards import main_menu_keyboard
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="menu")


@router.message(Command("menu"))
async def open_menu(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the menu when a profile already exists."""
    profile = await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )
    if profile is None:
        return
    await state.clear()
    await render_menu(state, message, update_main_message, create_new=True)


@router.callback_query(MenuCallback.filter(F.section == MenuSection.HOME))
async def return_to_menu(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Discard transient input and return to the main screen."""
    await state.clear()
    await query.answer()
    await render_menu(state, query, update_main_message)


async def render_menu(
    state: FSMContext,
    event: Message | CallbackQueryWithMessage,
    update_main_message: UpdateMainMessage,
    *,
    create_new: bool = False,
) -> None:
    """Render the central navigation screen."""
    await update_main_message(
        state,
        event,
        TEXTS[TextKey.MENU_TITLE],
        reply_markup=main_menu_keyboard(),
        create_new=create_new,
    )

"""Maintain one editable bot screen for an interactive flow."""

from typing import Protocol, cast

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.sender import Sender


class UpdateMainMessage(Protocol):
    """Update the current interactive screen for a message or callback event."""

    async def __call__(
        self,
        state: FSMContext,
        event: Message | CallbackQueryWithMessage,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        *,
        create_new: bool = False,
    ) -> None: ...


async def update_main_message(
    sender: Sender,
    state: FSMContext,
    event: Message | CallbackQueryWithMessage,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    create_new: bool = False,
) -> None:
    """Edit the current screen when possible, otherwise create a replacement."""
    source = event if isinstance(event, Message) else event.message
    is_user_message = isinstance(event, Message)
    if not is_user_message:
        await cast(CallbackQueryWithMessage, event).answer()
    main_message_id = (await state.get_data()).get("main_message_id")
    target_message_id = main_message_id
    if not is_user_message and source.message_id != main_message_id:
        target_message_id = source.message_id
    if not create_new and isinstance(target_message_id, int):
        updated = await sender.edit_by_id(
            source.chat.id, target_message_id, text, reply_markup
        )
        if updated:
            if is_user_message:
                await sender.delete(source)
            await state.update_data(main_message_id=target_message_id)
            return
    created = await sender.answer(source, text, reply_markup)
    if created is not None:
        await state.update_data(main_message_id=created.message_id)

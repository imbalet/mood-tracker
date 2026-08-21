"""Maintain one editable bot screen for an interactive flow."""

from typing import TYPE_CHECKING, Protocol, cast

from aiogram.types import InlineKeyboardMarkup, InputRichMessage, Message

from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.utils.sender import Sender

if TYPE_CHECKING:
    from mood_tracker.presentation.screens.screen import Screen, ScreenContent


class UpdateMainMessage(Protocol):
    """Update the current interactive screen for a message or callback event."""

    async def __call__(
        self,
        content: Screen | ScreenContent,
        reply_markup: InlineKeyboardMarkup | None = None,
        *,
        create_new: bool = False,
    ) -> None: ...


async def update_main_message(
    sender: Sender,
    presentation_data: PresentationData,
    event: Message | CallbackQueryWithMessage,
    content: Screen | ScreenContent,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    create_new: bool = False,
) -> None:
    """Edit the current screen when possible, otherwise create a replacement."""
    if isinstance(content, Screen):
        screen = content.render()
        content = screen.content
        reply_markup = screen.reply_markup
    source = event if isinstance(event, Message) else event.message
    is_user_message = isinstance(event, Message)
    if not is_user_message:
        await cast(CallbackQueryWithMessage, event).answer()
    main_message_id = await presentation_data.main_message_id()
    target_message_id = main_message_id
    if not is_user_message and source.message_id != main_message_id:
        target_message_id = source.message_id
    if not create_new and isinstance(target_message_id, int):
        if isinstance(content, InputRichMessage):
            updated = await sender.edit_rich_by_id(
                source.chat.id, target_message_id, content, reply_markup
            )
        else:
            updated = await sender.edit_by_id(
                source.chat.id, target_message_id, content, reply_markup
            )
        if updated:
            if is_user_message:
                await sender.delete(source)
            await presentation_data.set_main_message_id(target_message_id)
            return
    if isinstance(content, InputRichMessage):
        created = await sender.answer_rich(source, content, reply_markup)
    else:
        created = await sender.answer(source, content, reply_markup)
    if created is not None:
        if not create_new and isinstance(target_message_id, int):
            await sender.delete_by_id(source.chat.id, target_message_id)
        await presentation_data.set_main_message_id(created.message_id)

"""Translate expected presentation failures into Telegram feedback."""

import logging

from aiogram.types import CallbackQuery, ErrorEvent, Message, Update

from mood_tracker.presentation.constants import TEXTS, TextKey

logger = logging.getLogger(__name__)


async def handle_stale_callback(event: ErrorEvent) -> bool:
    """Notify the user that a callback button can no longer be used."""
    callback = event.update.callback_query
    if callback is not None:
        await callback.answer(TEXTS[TextKey.STALE_BUTTON], show_alert=True)
    return True


async def handle_application_error(event: ErrorEvent) -> bool:
    """Log an unhandled application failure and give a safe user response."""
    _log_failure("Unhandled application error", event)
    await _notify_failure(event.update)
    return True


async def handle_unexpected_error(event: ErrorEvent) -> bool:
    """Log every remaining exception with update metadata for investigation."""
    _log_failure("Unhandled unexpected error", event)
    await _notify_failure(event.update)
    return True


def _log_failure(summary: str, event: ErrorEvent) -> None:
    """Log a traceback and safe identifiers without diary-message content."""
    update = event.update
    logger.exception(
        "%s: exception_type=%s update_id=%s %s",
        summary,
        type(event.exception).__name__,
        update.update_id,
        _update_context(update),
    )


def _update_context(update: Update) -> str:
    """Build diagnostic context while intentionally excluding message text."""
    if update.callback_query is not None:
        query = update.callback_query
        return (
            "kind=callback "
            f"telegram_id={query.from_user.id} chat_id={_chat_id(query)} "
            f"message_id={_message_id(query)} callback_data={query.data!r}"
        )
    if update.message is not None:
        message = update.message
        return (
            "kind=message "
            f"telegram_id={message.from_user.id if message.from_user else None} "
            f"chat_id={message.chat.id} message_id={message.message_id}"
        )
    return "kind=other"


async def _notify_failure(update: Update) -> None:
    """Send generic feedback without leaking exception details to the user."""
    if update.callback_query is not None:
        await update.callback_query.answer(
            TEXTS[TextKey.OPERATION_FAILED], show_alert=True
        )
        return
    if update.message is not None:
        await update.message.answer(TEXTS[TextKey.OPERATION_FAILED])


def _chat_id(query: CallbackQuery) -> int | None:
    message = query.message
    return message.chat.id if isinstance(message, Message) else None


def _message_id(query: CallbackQuery) -> int | None:
    message = query.message
    return message.message_id if isinstance(message, Message) else None

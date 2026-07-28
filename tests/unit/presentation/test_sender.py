from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from mood_tracker.presentation.sender import _is_not_modified


def test_not_modified_error_is_a_successful_noop() -> None:
    error = TelegramBadRequest(
        EditMessageText(chat_id=1, message_id=1, text="same"),
        "Bad Request: message is not modified",
    )

    assert _is_not_modified(error)


def test_other_bad_request_is_not_a_noop() -> None:
    error = TelegramBadRequest(
        EditMessageText(chat_id=1, message_id=1, text="same"),
        "Bad Request: message to edit not found",
    )

    assert not _is_not_modified(error)

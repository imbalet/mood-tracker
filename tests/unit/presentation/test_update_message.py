from datetime import datetime
from unittest.mock import AsyncMock

from aiogram.types import Chat, Message, User

from mood_tracker.presentation.screens.menu import MainMenuScreen
from mood_tracker.presentation.utils.sender import Sender
from mood_tracker.presentation.utils.update_message import update_main_message


async def test_update_main_message_renders_screen_before_sending(mocker) -> None:
    sender = mocker.create_autospec(Sender, instance=True)
    sender.answer = AsyncMock(return_value=None)
    presentation_data = mocker.Mock()
    presentation_data.main_message_id = AsyncMock(return_value=None)
    event = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=123, type="private"),
        from_user=User(id=123, is_bot=False, first_name="Test"),
        text="/test",
    )

    await update_main_message(
        sender, presentation_data, event, MainMenuScreen(), create_new=True
    )

    sender.answer.assert_awaited_once()

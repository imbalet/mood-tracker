from aiogram.types import InputRichMessage

from mood_tracker.presentation.screens import ScreenResult


def test_screen_accepts_rich_content() -> None:
    content = InputRichMessage(html="<b>Палитра</b>")

    screen = ScreenResult(content)

    assert screen.content is content
    assert screen.reply_markup is None

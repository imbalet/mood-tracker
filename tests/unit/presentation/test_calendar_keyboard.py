from datetime import date

from aiogram.types import BufferedInputFile, InputRichMessage

from mood_tracker.presentation.callbacks.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.screens.calendar import CalendarImageScreen


def _calendar_screen():
    return CalendarImageScreen(
        image=BufferedInputFile(b"png", filename="calendar.png"),
        can_go_next=False,
        month=date(2025, 2, 1),
    ).render()


def test_calendar_image_keyboard_has_menu_button() -> None:
    screen = _calendar_screen()
    assert screen.reply_markup is not None

    button = screen.reply_markup.inline_keyboard[-1][0]

    assert button.text == "🏠 В меню"
    assert MenuCallback.unpack(button.callback_data).section is MenuSection.HOME


def test_calendar_screen_embeds_the_png_as_editable_rich_media() -> None:
    screen = _calendar_screen()

    assert isinstance(screen.content, InputRichMessage)
    assert screen.content.media is not None
    assert screen.content.media[0].id == "calendar"

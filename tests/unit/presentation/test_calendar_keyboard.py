from datetime import date

from aiogram.types import BufferedInputFile, InputRichMessage

from mood_tracker.presentation.callbacks import MenuCallback, MenuSection
from mood_tracker.presentation.handlers.calendar import _image_keyboard
from mood_tracker.presentation.screens import month_calendar_screen


def test_calendar_image_keyboard_has_menu_button() -> None:
    keyboard = _image_keyboard(date(2025, 2, 1), can_go_next=False)

    button = keyboard.inline_keyboard[-1][0]

    assert button.text == "В меню"
    assert MenuCallback.unpack(button.callback_data).section is MenuSection.HOME


def test_calendar_screen_embeds_the_png_as_editable_rich_media() -> None:
    screen = month_calendar_screen(
        BufferedInputFile(b"png", filename="calendar.png"),
        _image_keyboard(date(2025, 2, 1), can_go_next=False),
    )

    assert isinstance(screen.content, InputRichMessage)
    assert screen.content.media is not None
    assert screen.content.media[0].id == "calendar"

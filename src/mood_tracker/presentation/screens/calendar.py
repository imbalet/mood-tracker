"""Rich Telegram screen for the rendered diary calendar."""

from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichMessage,
)
from aiogram.types.input_rich_message_media import InputRichMessageMedia

from mood_tracker.presentation.screens.screen import Screen


def month_calendar_screen(
    image: BufferedInputFile, reply_markup: InlineKeyboardMarkup
) -> Screen:
    """Embed one PNG calendar so Telegram can edit it in place later."""
    return Screen(
        InputRichMessage(
            html='<img src="tg://photo?id=calendar"/>',
            media=[
                InputRichMessageMedia(id="calendar", media=InputMediaPhoto(media=image))
            ],
        ),
        reply_markup,
    )

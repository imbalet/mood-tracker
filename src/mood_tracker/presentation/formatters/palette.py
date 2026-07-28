"""Rich-message formatting for the exact core-state color legend."""

from aiogram.types import InputMediaPhoto, InputRichMessage, InputRichMessageMedia

from mood_tracker.domain.entities import ScaleConfig, StatePalette
from mood_tracker.presentation.palette_preview import render_palette_preview


def format_palette_message(
    config: ScaleConfig, palette: StatePalette
) -> InputRichMessage:
    """Embed a numbered calendar-color scale as one rich-message photo block."""
    return InputRichMessage(
        html=(
            "<h3>Палитра состояния</h3>"
            '<img src="tg://photo?id=scale"/>'
            "<p><code>"
            f"{palette.minimum} → {palette.middle} → {palette.maximum}"
            "</code></p>"
        ),
        media=[
            InputRichMessageMedia(
                id="scale",
                media=InputMediaPhoto(media=render_palette_preview(config, palette)),
            ),
        ],
    )

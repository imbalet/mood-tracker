from mood_tracker.domain.entities import ScaleConfig, StatePalette
from mood_tracker.presentation.formatters import format_palette_message


def test_palette_message_embeds_numbered_preview() -> None:
    palette = StatePalette("#112233", "#445566", "#778899")

    message = format_palette_message(ScaleConfig(0, 10), palette)

    assert message.html and message.media
    assert 'src="tg://photo?id=scale"' in message.html
    assert message.media[0].id == "scale"
    assert "#112233 → #445566 → #778899" in message.html

from io import BytesIO

from PIL import Image

from mood_tracker.domain.entities import ScaleConfig, StatePalette
from mood_tracker.presentation.rendering.palette_preview import render_palette_preview


def test_palette_preview_uses_exact_anchor_colors() -> None:
    preview = render_palette_preview(
        ScaleConfig(0, 2),
        StatePalette("#112233", "#445566", "#778899"),
    )

    image = Image.open(BytesIO(preview.data)).convert("RGB")

    assert image.getpixel((13, 20)) == (17, 34, 51)
    assert image.getpixel((52, 20)) == (68, 85, 102)
    assert image.getpixel((91, 20)) == (119, 136, 153)

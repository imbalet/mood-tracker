"""Render the exact calendar-color legend for one core Scale configuration."""

from io import BytesIO

from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw, ImageFont

from mood_tracker.domain.entities import ScaleConfig, StatePalette

_CELL_SIZE = 36
_GAP = 3
_PADDING = 8
_MAX_COLUMNS = 11
_BACKGROUND = "#FFFFFF"


def render_palette_preview(
    config: ScaleConfig, palette: StatePalette
) -> BufferedInputFile:
    """Return a PNG whose cells match every possible calendar-day color."""
    values = tuple(range(config.minimum, config.maximum + 1))
    columns = min(len(values), _MAX_COLUMNS)
    rows = (len(values) + columns - 1) // columns
    width = _PADDING * 2 + columns * _CELL_SIZE + (columns - 1) * _GAP
    height = _PADDING * 2 + rows * _CELL_SIZE + (rows - 1) * _GAP
    image = Image.new("RGB", (width, height), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=13)
    for index, value in enumerate(values):
        row, column = divmod(index, columns)
        left = _PADDING + column * (_CELL_SIZE + _GAP)
        top = _PADDING + row * (_CELL_SIZE + _GAP)
        color = _interpolate_color(value, config, palette)
        draw.rounded_rectangle(
            (left, top, left + _CELL_SIZE, top + _CELL_SIZE), radius=5, fill=color
        )
        label = str(value)
        box = draw.textbbox((0, 0), label, font=font)
        text_x = left + (_CELL_SIZE - (box[2] - box[0])) / 2
        text_y = top + (_CELL_SIZE - (box[3] - box[1])) / 2 - box[1]
        draw.text((text_x, text_y), label, fill=_text_color(color), font=font)
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return BufferedInputFile(buffer.getvalue(), filename="palette-scale.png")


def _interpolate_color(value: int, config: ScaleConfig, palette: StatePalette) -> str:
    normalized = (value - config.minimum) / (config.maximum - config.minimum)
    if normalized <= 0.5:
        return _mix(palette.minimum, palette.middle, normalized * 2)
    return _mix(palette.middle, palette.maximum, (normalized - 0.5) * 2)


def _mix(start: str, end: str, ratio: float) -> str:
    start_rgb = tuple(int(start[index : index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(
        round(left + (right - left) * ratio)
        for left, right in zip(start_rgb, end_rgb, strict=True)
    )
    return "#" + "".join(f"{component:02X}" for component in mixed)


def _text_color(background: str) -> str:
    red, green, blue = (int(background[index : index + 2], 16) for index in (1, 3, 5))
    luminance = (red * 299 + green * 587 + blue * 114) / 1000
    return "#000000" if luminance > 150 else "#FFFFFF"

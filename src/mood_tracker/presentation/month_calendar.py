"""Server-side PNG rendering for one personal diary month."""

import calendar
from datetime import date
from functools import cache
from io import BytesIO
from pathlib import Path
from uuid import UUID

from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw, ImageFont

from mood_tracker.application.commands import MonthCalendar
from mood_tracker.domain.entities import Day, Field, ScaleConfig
from mood_tracker.domain.enums import DayStatus, FieldType
from mood_tracker.presentation.palette_preview import interpolate_state_color

_CELL = 76
_PADDING = 26
_HEADER = 80
_BACKGROUND = "#FFFFFF"
_EMPTY = "#E6E8EB"
_DRAFT = "#6B7280"
_ORDINAL_MARKER_MIN_SIZE = 14
_ORDINAL_MARKER_MAX_SIZE = 28
_WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_MONTHS = (
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
)
_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_TEXT_FONT_PATH = _FONT_DIR / "NotoSans-Regular.ttf"
_EMOJI_FONT_PATH = _FONT_DIR / "NotoColorEmoji.ttf"
_EMOJI_FONT_SIZE = 109


def render_month_calendar(data: MonthCalendar) -> BufferedInputFile:
    """Render a compact month image from already owner-scoped diary data."""
    weeks = calendar.monthcalendar(data.month.year, data.month.month)
    width = _PADDING * 2 + _CELL * 7
    height = _HEADER + _PADDING + _CELL * (len(weeks) + 1)
    image = Image.new("RGBA", (width, height), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    title_font = _text_font(18)
    font = _text_font(18)
    draw.text(
        (_PADDING, 18),
        f"{_MONTHS[data.month.month - 1].capitalize()} {data.month.year}",
        fill="#111827",
        font=title_font,
    )
    for column, label in enumerate(_WEEKDAYS):
        _centered_text(draw, _PADDING + column * _CELL, _HEADER, _CELL, label, font)

    days = {day.date: day for day in data.days}
    fields = {field.id: field for field in data.fields}
    core = next((field for field in data.fields if field.is_core), None)
    for row, week in enumerate(weeks):
        for column, day_number in enumerate(week):
            if day_number == 0:
                continue
            target = date(data.month.year, data.month.month, day_number)
            left = _PADDING + column * _CELL
            top = _HEADER + _CELL // 2 + row * _CELL
            diary_day = days.get(target)
            color = _day_color(diary_day, core)
            center = (left + _CELL // 2, top + _CELL // 2 + 4)
            draw.ellipse(
                (center[0] - 24, center[1] - 24, center[0] + 24, center[1] + 24),
                fill=color,
                outline=(
                    _DRAFT
                    if diary_day and diary_day.status is DayStatus.DRAFT
                    else None
                ),
                width=3,
            )
            _centered_text(draw, left, top + 28, _CELL, str(day_number), font)
            if diary_day is not None:
                _draw_ordinal_markers(image, draw, diary_day, fields, left, top, font)
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return BufferedInputFile(buffer.getvalue(), filename="mood-calendar.png")


def _day_color(day: Day | None, core: Field | None) -> str:
    if day is None or core is None:
        return _EMPTY
    value = day.values.get(core.id)
    palette = core.display_config.state_palette
    if value is None or value.normalized_value is None or palette is None:
        return _EMPTY
    config = core.get_version(value.field_version_id)
    if config is None or not isinstance(config.config, ScaleConfig):
        return _EMPTY
    if not isinstance(value.value, int):
        return _EMPTY
    return interpolate_state_color(value.value, config.config, palette)


def _draw_ordinal_markers(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    day: Day,
    fields: dict[UUID, Field],
    left: int,
    top: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    markers = [
        (
            field.display_config.emoji,
            field.name,
            _marker_size(value.normalized_value),
        )
        for field_id, value in day.values.items()
        if (field := fields.get(field_id)) is not None
        and (version := field.get_version(value.field_version_id)) is not None
        and version.type is FieldType.ORDINAL
        and field.display_config.show_in_calendar
        and field.display_config.emoji is not None
        and value.normalized_value is not None
        and value.normalized_value > 0
    ]
    for index, (emoji, name, size) in enumerate(markers[:2]):
        position = (left + 4 + index * 31, top + 3)
        if _has_emoji_glyph(emoji):
            _draw_emoji(image, emoji, position, size)
        else:
            _draw_marker_fallback(draw, name, position, size, font)


def _marker_size(normalized_value: float) -> int:
    """Interpolate every ordinal emoji within the common calendar range."""
    return round(
        _ORDINAL_MARKER_MIN_SIZE
        + normalized_value * (_ORDINAL_MARKER_MAX_SIZE - _ORDINAL_MARKER_MIN_SIZE)
    )


def _text_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the bundled Cyrillic font with Pillow's fallback for broken installs."""
    try:
        return ImageFont.truetype(_TEXT_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


@cache
def _emoji_font() -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(_EMOJI_FONT_PATH, _EMOJI_FONT_SIZE)
    except OSError:
        return None


def _has_emoji_glyph(emoji: str) -> bool:
    font = _emoji_font()
    if font is None:
        return False
    return bytes(font.getmask(emoji)) != bytes(font.getmask("\ufffd"))


def _draw_emoji(
    image: Image.Image, emoji: str, position: tuple[int, int], size: int
) -> None:
    font = _emoji_font()
    if font is None:
        return
    tile = Image.new("RGBA", (136, 128))
    ImageDraw.Draw(tile).text((0, 0), emoji, font=font, embedded_color=True)
    tile.thumbnail((size, size), Image.Resampling.LANCZOS)
    image.alpha_composite(tile, dest=position)


def _draw_marker_fallback(
    draw: ImageDraw.ImageDraw,
    field_name: str,
    position: tuple[int, int],
    size: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Keep a useful marker if a custom emoji has no glyph in Noto Color Emoji."""
    x, y = position
    draw.ellipse((x, y + 3, x + size, y + size + 3), fill="#4B5563")
    draw.text(
        (x + size / 3, y + size / 4),
        field_name[:1].upper(),
        fill="#FFFFFF",
        font=font,
    )


def _centered_text(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    width: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (left + (width - (box[2] - box[0])) / 2, top),
        text,
        fill="#111827",
        font=font,
    )

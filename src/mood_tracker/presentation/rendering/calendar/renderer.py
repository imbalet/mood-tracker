import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Literal, override

import skia
from pictex import Column, Element, Row, Text
from pictex import Image as PicTexImage
from pictex.models import BackgroundImage, CropMode, FontSmoothing
from pictex.renderer.renderer import Renderer
from PIL import Image, ImageChops, ImageColor, ImageDraw

type XYPair = tuple[int, int]
DotStyle = Literal["solid", "hatched"]
_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


@dataclass(slots=True)
class Constants:
    """Localized labels rendered in the calendar header and weekday row."""

    weekdays: tuple[str, ...] = ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")
    months: Mapping[int, str] = field(
        default_factory=lambda: {
            1: "Январь",
            2: "Февраль",
            3: "Март",
            4: "Апрель",
            5: "Май",
            6: "Июнь",
            7: "Июль",
            8: "Август",
            9: "Сентябрь",
            10: "Октябрь",
            11: "Ноябрь",
            12: "Декабрь",
        }
    )


@dataclass(slots=True)
class Header:
    height: int = 58
    radius: int = 14
    background: str = "#EAEFF5"
    text_color: str = "#1C2430"
    font_path: Path = _FONT_DIR / "NotoSans-Regular.ttf"
    font_size: int = 20
    font_weight: int = 700
    padding: XYPair = (0, 18)


@dataclass(slots=True)
class Weekday:
    """Shared geometry of weekday labels and day cards."""

    text_color: str = "#7A828E"
    font_size: int = 12
    font_weight: int = 600
    weekday_name_height: int = 28
    card_size: int = 96
    grid_gap: int = 10
    card_radius: int = 12
    day_number_size: int = 15
    grid_size: XYPair = (3, 3)  # (rows, columns) inside one day card
    grid_anchors: tuple[str, str, str] = ("16.6667%", "50%", "83.3333%")
    # Percentage anchor for each row and column of the card grid.


@dataclass(slots=True)
class DayNumber:
    """Position of the numeric day label in the card grid."""

    position: XYPair = (0, 0)


@dataclass(slots=True)
class StatusDot:
    """Size and position of the core-state marker."""

    size: int = 40
    position: XYPair = (1, 1)


@dataclass(slots=True)
class Emoji:
    """Slots and typography for non-core field emoji."""

    positions: tuple[XYPair, ...] = ((0, 2), (1, 2), (2, 0), (2, 1), (2, 2))
    font_path: Path = _FONT_DIR / "NotoColorEmoji.ttf"
    size: int = 22
    gap: int = 0


@dataclass(slots=True)
class Config:
    """Renderer-only layout and typography configuration."""

    constants: Constants = field(default_factory=Constants)
    header: Header = field(default_factory=Header)
    weekday: Weekday = field(default_factory=Weekday)
    day_number: DayNumber = field(default_factory=DayNumber)
    status_dot: StatusDot = field(default_factory=StatusDot)
    emoji: Emoji = field(default_factory=Emoji)
    first_weekday: calendar.Day = calendar.Day.MONDAY
    background: str = "#FFFFFF"
    outer_padding: int = 30
    content_gap: int = 12

    @property
    def calendar_width(self) -> int:
        columns = len(self.constants.weekdays)
        return self.weekday.card_size * columns + self.weekday.grid_gap * max(
            columns - 1, 0
        )

    @property
    def root_width(self) -> int:
        return self.calendar_width + self.outer_padding * 2


@dataclass(frozen=True, slots=True)
class DayInfo:
    """Fully resolved appearance of a real calendar date."""

    background: str = "#F7F8FA"
    text_color: str = "#22252A"
    border_color: str | None = None
    border_width: float = 1.5
    dot_color: str | None = None
    dot_style: DotStyle = "solid"
    # `None` preserves a field's reserved emoji slot when it has no value today.
    emojis: tuple[str | None, ...] = ()

    def __post_init__(self) -> None:
        if self.border_width <= 0:
            raise ValueError("border_width must be positive")
        if self.dot_style not in ("solid", "hatched"):
            raise ValueError(f"Unknown dot style: {self.dot_style!r}")


@lru_cache(maxsize=128)
def _hatched_dot(color: str, size: int) -> bytes:
    render_size = size * 4
    mask = Image.new("L", (render_size, render_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((4, 4, render_size - 5, render_size - 5), fill=255)
    hatch = Image.new("L", (render_size, render_size), 0)
    hatch_draw = ImageDraw.Draw(hatch)
    for x in range(-render_size, render_size * 2, 40):
        hatch_draw.line((x, render_size, x + render_size, 0), fill=255, width=8)
    alpha = ImageChops.multiply(mask, hatch)
    draw = ImageDraw.Draw(alpha)
    draw.ellipse((4, 4, render_size - 5, render_size - 5), outline=255, width=4)
    image = Image.new(
        "RGBA", (render_size, render_size), (*ImageColor.getrgb(color), 255)
    )
    image.putalpha(alpha)
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    with BytesIO() as output:
        image.save(output, "PNG")
        return output.getvalue()


class _MemoryBackgroundImage(BackgroundImage):
    def __init__(self, image: skia.Image) -> None:
        super().__init__(path="")
        self._skia_image = image

    @override
    def __deepcopy__(self, memo: dict[int, object]) -> _MemoryBackgroundImage:
        del memo
        return _MemoryBackgroundImage(self._skia_image)


def _png_image(data: bytes) -> PicTexImage:
    decoded = skia.Image.MakeFromEncoded(data)
    if decoded is None:
        raise ValueError("Unable to decode generated dot PNG")
    # PicTex has no public constructor for an in-memory background image.
    # Keep this private-style access isolated for PicTex upgrade checks.
    image = PicTexImage("")
    image._style.background_image.set(_MemoryBackgroundImage(decoded))
    return image


class _OwnedRow(Row):
    """PicTex row for children created exclusively for one calendar render."""

    @override
    def _parse_children(self, *children: Element | str) -> list[Element]:
        return [Text(child) if isinstance(child, str) else child for child in children]


class _OwnedColumn(Column):
    """PicTex column that avoids defensive copies of one-use child builders."""

    @override
    def _parse_children(self, *children: Element | str) -> list[Element]:
        return [Text(child) if isinstance(child, str) else child for child in children]


class CalendarRenderer:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    @staticmethod
    def _fixed_square(element: Element, size: int) -> Element:
        """Prevent PicTex flex sizing from distorting a round status marker."""
        return (
            element.size(width=size, height=size)
            .min_width(size)
            .max_width(size)
            .min_height(size)
            .max_height(size)
            .aspect_ratio(1)
            .flex_shrink(0)
        )

    def _status_dot(self, color: str, dot_style: DotStyle) -> Element:
        size = self.config.status_dot.size
        if dot_style == "solid":
            return self._fixed_square(
                _OwnedRow().background_color(color).border_radius("50%"), size
            )
        if dot_style == "hatched":
            return self._fixed_square(_png_image(_hatched_dot(color, size)), size)
        raise ValueError(f"Unknown dot style: {dot_style!r}")

    def render_calendar(
        self, *, year: int, month: int, day_data: Mapping[int, DayInfo]
    ) -> bytes:
        layout = self.make_calendar(year=year, month=month, day_data=day_data)
        image = Renderer().render_as_bitmap(  # type: ignore[no-untyped-call]
            layout._to_node(),  # The layout is a fresh, owned tree.
            CropMode.NONE,
            FontSmoothing.SUBPIXEL,
        )
        encoded = image.skia_image.encodeToData(skia.EncodedImageFormat.kPNG, 100)
        if encoded is None:
            raise RuntimeError("Failed to encode calendar PNG")
        return bytes(encoded.bytes())

    def make_calendar(
        self, *, year: int, month: int, day_data: Mapping[int, DayInfo]
    ) -> Column:
        self._validate_days(year, month, day_data)
        config = self.config
        header = (
            _OwnedColumn(
                Text(f"{config.constants.months[month]} {year}")
                .font_family(config.header.font_path)
                .font_size(config.header.font_size)
                .font_weight(config.header.font_weight)
                .color(config.header.text_color)
            )
            .size(width="auto", height=config.header.height)
            .padding(*config.header.padding)
            .justify_content("center")
            .align_items("start")
            .background_color(config.header.background)
            .border_radius(config.header.radius)
        )
        weekdays = _OwnedRow(
            *[
                _OwnedRow(
                    Text(name)
                    .font_size(config.weekday.font_size)
                    .font_weight(config.weekday.font_weight)
                    .color(config.weekday.text_color)
                )
                .size(
                    width=config.weekday.card_size,
                    height=config.weekday.weekday_name_height,
                )
                .justify_content("center")
                .align_items("center")
                for name in config.constants.weekdays
            ]
        ).gap(config.weekday.grid_gap)
        weeks = self._month_weeks(year, month)
        grid = (
            _OwnedColumn(weekdays, *[self._week(week, day_data) for week in weeks])
            .gap(config.weekday.grid_gap)
            .size(width=config.calendar_width)
        )
        return (
            _OwnedColumn(header, grid)
            .size(width=config.root_width)
            .padding(config.outer_padding)
            .gap(config.content_gap)
            .background_color(config.background)
        )

    def _validate_days(
        self, year: int, month: int, data: Mapping[int, DayInfo]
    ) -> None:
        expected = set(range(1, calendar.monthrange(year, month)[1] + 1))
        if set(data) != expected:
            raise ValueError("day_data must contain every real day of the month")
        if any(not isinstance(info, DayInfo) for info in data.values()):
            raise TypeError("day_data values must be DayInfo")
        if len(self.config.constants.weekdays) != 7:
            raise ValueError("Exactly seven weekday names are required")

    def _month_weeks(self, year: int, month: int) -> list[list[int]]:
        try:
            calendar.monthrange(year, month)
        except (calendar.IllegalMonthError, ValueError) as error:
            raise ValueError(f"Invalid year/month: {year}-{month}") from error
        weeks = calendar.Calendar(self.config.first_weekday).monthdayscalendar(
            year, month
        )
        weeks.extend([[0] * 7 for _ in range(6 - len(weeks))])
        return weeks

    def _week(self, week: Sequence[int], data: Mapping[int, DayInfo]) -> Row:
        cells = [
            self.make_empty_day() if day == 0 else self.make_day_card(day, data[day])
            for day in week
        ]
        return _OwnedRow(*cells).gap(self.config.weekday.grid_gap)

    def make_empty_day(self) -> Row:
        size = self.config.weekday.card_size
        return _OwnedRow().size(width=size, height=size)

    def make_day_card(self, day: int, info: DayInfo | None = None) -> Element:
        info = info or DayInfo()
        style, size = self.config, self.config.weekday.card_size
        children: list[Element] = [
            self._place(
                Text(str(day))
                .font_size(style.weekday.day_number_size)
                .font_weight(700)
                .color(info.text_color),
                style.day_number.position,
            )
        ]
        if info.dot_color is not None:
            children.append(
                self._place(
                    self._status_dot(info.dot_color, info.dot_style),
                    style.status_dot.position,
                )
            )
        if info.emojis:
            children.append(self._emoji_grid(info.emojis))
        card = (
            _OwnedColumn(*children)
            .size(width=size, height=size)
            .background_color(info.background)
            .border_radius(style.weekday.card_radius)
        )
        return (
            card
            if info.border_color is None
            else card.border(info.border_width, info.border_color)
        )

    def _place(self, element: Element, position: XYPair) -> Element:
        row, column = position
        anchors = self.config.weekday.grid_anchors
        rows, columns = self.config.weekday.grid_size
        if not 0 <= row < rows or not 0 <= column < columns:
            raise ValueError(f"Position {position!r} is outside {rows}x{columns}")
        if len(anchors) < max(rows, columns):
            raise ValueError(
                "grid_anchors must cover every configured grid row and column"
            )
        return (
            element.absolute_position(top=anchors[row], left=anchors[column])
            .translate(x="-50%", y="-50%")
            .flex_shrink(0)
        )

    def _emoji_grid(self, emojis: Sequence[str | None]) -> Column:
        config = self.config
        if len(emojis) > len(config.emoji.positions):
            raise ValueError("Too many emojis for the configured calendar card")
        rows, columns = config.weekday.grid_size
        values: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        for emoji, (row, column) in zip(emojis, config.emoji.positions):
            if not 0 <= row < rows or not 0 <= column < columns:
                raise ValueError(
                    f"Emoji position {(row, column)!r} is outside {rows}x{columns}"
                )
            values[row][column] = emoji
        slot_width = config.weekday.card_size // columns
        slot_height = config.weekday.card_size // rows
        grid_rows = [
            _OwnedRow(
                *[self._emoji_slot(value, slot_width, slot_height) for value in row]
            ).gap(config.emoji.gap)
            for row in values
        ]
        return (
            _OwnedColumn(*grid_rows)
            .gap(config.emoji.gap)
            .size(width=config.weekday.card_size, height=config.weekday.card_size)
            .absolute_position(top=0, left=0)
        )

    def _emoji_slot(self, emoji: str | None, width: int, height: int) -> Row:
        if emoji is None:
            return _OwnedRow().size(width=width, height=height)
        return (
            _OwnedRow(
                Text(emoji)
                .font_family(self.config.emoji.font_path)
                .font_size(self.config.emoji.size)
            )
            .size(width=width, height=height)
            .justify_content("center")
            .align_items("center")
        )

    def render_to_file(
        self,
        path: str | Path,
        *,
        year: int,
        month: int,
        day_data: Mapping[int, DayInfo],
    ) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(
            self.render_calendar(year=year, month=month, day_data=day_data)
        )
        return output

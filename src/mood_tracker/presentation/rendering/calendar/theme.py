from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from mood_tracker.presentation.rendering.calendar.renderer import Config, DotStyle


class DayBackgroundMode(StrEnum):
    """Whether completed-day backgrounds stay neutral or tint from the status dot."""

    UNIFORM = "uniform"
    STATUS_TINT = "status_tint"


@dataclass(frozen=True, slots=True)
class DayStyle:
    """Complete card style before draft, tint and record overrides."""

    background: str = "#F7F8FA"
    text_color: str = "#22252A"
    border_color: str | None = None
    border_width: float = 1.5
    dot_style: DotStyle = "solid"

    def __post_init__(self) -> None:
        if self.border_width <= 0:
            raise ValueError("border_width must be positive")

    def with_background(self, background: str) -> DayStyle:
        return DayStyle(
            background=background,
            text_color=self.text_color,
            border_color=self.border_color,
            border_width=self.border_width,
            dot_style=self.dot_style,
        )


class _Unset:
    """Differentiate inherited values from an explicit nullable override."""


UNSET = _Unset()


@dataclass(frozen=True, slots=True)
class DayStyleOverride:
    """Partial style applied over the previous stage of the day-style cascade."""

    background: str | _Unset = UNSET
    text_color: str | _Unset = UNSET
    border_color: str | None | _Unset = UNSET
    border_width: float | _Unset = UNSET
    dot_style: DotStyle | _Unset = UNSET

    def apply_to(self, base: DayStyle) -> DayStyle:
        return DayStyle(
            background=(
                base.background
                if self.background is UNSET
                else cast(str, self.background)
            ),
            text_color=(
                base.text_color
                if self.text_color is UNSET
                else cast(str, self.text_color)
            ),
            border_color=(
                base.border_color
                if self.border_color is UNSET
                else cast(str | None, self.border_color)
            ),
            border_width=(
                base.border_width
                if self.border_width is UNSET
                else cast(float, self.border_width)
            ),
            dot_style=(
                base.dot_style
                if self.dot_style is UNSET
                else cast(DotStyle, self.dot_style)
            ),
        )


@dataclass(frozen=True, slots=True)
class CalendarVisualPolicy:
    """Resolve empty, filled, draft and record day styles in order."""

    empty_day: DayStyle = DayStyle()
    filled_day: DayStyleOverride = DayStyleOverride()
    draft_day: DayStyleOverride = DayStyleOverride(dot_style="hatched")
    best_record: DayStyleOverride = DayStyleOverride(
        border_color="#36A269", border_width=2
    )
    worst_record: DayStyleOverride = DayStyleOverride(
        border_color="#D84A4A", border_width=2
    )
    day_background_mode: DayBackgroundMode = DayBackgroundMode.UNIFORM
    status_tint_opacity: float = 0.16  # Used only in STATUS_TINT mode.

    def __post_init__(self) -> None:
        if not 0 <= self.status_tint_opacity <= 1:
            raise ValueError("status_tint_opacity must be in the 0..1 range")


@dataclass(slots=True)
class CalendarTheme:
    """Built-in theme boundary; JSON loading is deliberately not integrated yet."""

    renderer: Config = field(default_factory=Config)
    mapping: CalendarVisualPolicy = field(default_factory=CalendarVisualPolicy)

    @classmethod
    def default(cls) -> CalendarTheme:
        return cls()

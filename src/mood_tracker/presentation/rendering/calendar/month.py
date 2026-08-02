import calendar
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from aiogram.types import BufferedInputFile

from mood_tracker.application.commands import MonthCalendar
from mood_tracker.domain.entities import Field
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    DayStatus,
    QuestionnaireFieldRole,
    ReferenceType,
)
from mood_tracker.presentation.rendering.calendar.orchestrator import (
    RenderedImage,
    RenderOrchestrator,
    VisualizationKind,
)
from mood_tracker.presentation.rendering.calendar.renderer import (
    CalendarRenderer,
    DayInfo,
)
from mood_tracker.presentation.rendering.calendar.theme import (
    CalendarTheme,
    DayBackgroundMode,
    DayStyle,
)


@dataclass(frozen=True, slots=True)
class FieldData:
    """Only field attributes needed to prepare a calendar image."""

    id: UUID
    is_core: bool
    sort_order: int
    emoji: str | None
    show_in_calendar: bool
    state_palette: tuple[str, str, str] | None


@dataclass(frozen=True, slots=True)
class DayValueData:
    normalized_value: float | None


@dataclass(frozen=True, slots=True)
class DayData:
    """Aggregated facts for one diary date, independent of the renderer."""

    date: date
    status: DayStatus
    record_types: frozenset[ReferenceType]
    values: Mapping[UUID, DayValueData]


@dataclass(frozen=True, slots=True)
class DiaryVisualizationData:
    days: tuple[DayData, ...]
    fields: tuple[FieldData, ...]


@dataclass(frozen=True, slots=True)
class MonthCalendarRequest:
    """Input DTO for the month-calendar visualization."""

    month: date
    data: DiaryVisualizationData
    kind: VisualizationKind = field(
        init=False, default=VisualizationKind.MONTH_CALENDAR
    )


class MonthCalendarMapper:
    """Resolve diary facts into a complete, renderer-only month model."""

    def __init__(self, theme: CalendarTheme, max_emojis: int) -> None:
        self._theme = theme
        self._max_emojis = max_emojis

    def map(self, request: MonthCalendarRequest) -> dict[int, DayInfo]:
        policy = self._theme.mapping
        days_in_month = calendar.monthrange(request.month.year, request.month.month)[1]
        result = {
            day: self._day_info(policy.empty_day) for day in range(1, days_in_month + 1)
        }
        fields = {field.id: field for field in request.data.fields}
        core = next((field for field in fields.values() if field.is_core), None)
        for day in request.data.days:
            if (
                day.date.year == request.month.year
                and day.date.month == request.month.month
            ):
                result[day.date.day] = self._map_day(day, fields, core)
        return result

    def _map_day(
        self, day: DayData, fields: Mapping[UUID, FieldData], core: FieldData | None
    ) -> DayInfo:
        style = self._theme.mapping.filled_day.apply_to(self._theme.mapping.empty_day)
        if day.status is DayStatus.DRAFT:
            style = self._theme.mapping.draft_day.apply_to(style)
        dot_color = self._state_color(day, core)
        if (
            self._theme.mapping.day_background_mode is DayBackgroundMode.STATUS_TINT
            and dot_color is not None
        ):
            style = style.with_background(
                _blend(
                    style.background, dot_color, self._theme.mapping.status_tint_opacity
                )
            )
        if len(day.record_types) == 1:
            record = next(iter(day.record_types))
            override = (
                self._theme.mapping.best_record
                if record is ReferenceType.BEST
                else self._theme.mapping.worst_record
            )
            style = override.apply_to(style)
        emoji_fields = sorted(
            (
                field
                for field in fields.values()
                if not field.is_core
                and field.show_in_calendar
                and field.emoji is not None
            ),
            key=lambda item: item.sort_order,
        )[: self._max_emojis]
        emojis = tuple(
            field.emoji
            if (value := day.values.get(field.id)) is not None
            and value.normalized_value is not None
            and value.normalized_value > 0
            else None
            for field in emoji_fields
        )
        return self._day_info(style, dot_color=dot_color, emojis=emojis)

    def _state_color(self, day: DayData, core: FieldData | None) -> str | None:
        if core is None or core.state_palette is None:
            return None
        value = day.values.get(core.id)
        if value is None or value.normalized_value is None:
            return None
        return _palette_color(value.normalized_value, core.state_palette)

    @staticmethod
    def _day_info(
        style: DayStyle,
        *,
        dot_color: str | None = None,
        emojis: tuple[str | None, ...] = (),
    ) -> DayInfo:
        return DayInfo(
            background=style.background,
            text_color=style.text_color,
            border_color=style.border_color,
            border_width=style.border_width,
            dot_color=dot_color,
            dot_style=style.dot_style,
            emojis=emojis,
        )


class MonthCalendarVisualization:
    kind = VisualizationKind.MONTH_CALENDAR

    def __init__(self, theme: CalendarTheme) -> None:
        self._renderer = CalendarRenderer(theme.renderer)
        self._mapper = MonthCalendarMapper(theme, len(theme.renderer.emoji.positions))

    def render(self, request: object) -> RenderedImage:
        if not isinstance(request, MonthCalendarRequest):
            raise TypeError(
                "Month calendar visualization requires MonthCalendarRequest"
            )
        return RenderedImage(
            data=self._renderer.render_calendar(
                year=request.month.year,
                month=request.month.month,
                day_data=self._mapper.map(request),
            ),
            filename=f"mood-calendar-{request.month:%Y-%m}.png",
        )


class MonthCalendarImageService:
    def __init__(self, theme: CalendarTheme | None = None) -> None:
        visualization = MonthCalendarVisualization(theme or CalendarTheme.default())
        self._orchestrator = RenderOrchestrator((visualization,))

    def render(self, data: MonthCalendar) -> BufferedInputFile:
        image = self._orchestrator.render(
            MonthCalendarRequest(data.month, _to_visualization_data(data))
        )
        return BufferedInputFile(image.data, filename=image.filename)


def _to_visualization_data(source: MonthCalendar) -> DiaryVisualizationData:
    records: dict[UUID, set[ReferenceType]] = {}
    if source.references is not None:
        for day_id, reference_type in (
            (source.references.best_day_id, ReferenceType.BEST),
            (source.references.worst_day_id, ReferenceType.WORST),
        ):
            if day_id is not None:
                records.setdefault(day_id, set()).add(reference_type)
    return DiaryVisualizationData(
        days=tuple(
            DayData(
                date=day.date,
                status=day.status,
                record_types=frozenset(records.get(day.id, set())),
                values={
                    field_id: DayValueData(value.normalized_value)
                    for field_id, value in day.values.items()
                },
            )
            for day in source.days
        ),
        fields=tuple(
            _field_data(field, source.placements.get(field.id))
            for field in source.fields
        ),
    )


def _field_data(field: Field, placement: QuestionnaireField | None) -> FieldData:
    palette = field.display_config.state_palette
    return FieldData(
        id=field.id,
        is_core=(
            placement is not None and placement.role is QuestionnaireFieldRole.DAY_STATE
        ),
        sort_order=placement.sort_order if placement is not None else 0,
        emoji=field.display_config.emoji,
        show_in_calendar=field.display_config.show_in_calendar,
        state_palette=None
        if palette is None
        else (palette.minimum, palette.middle, palette.maximum),
    )


def _palette_color(value: float, palette: tuple[str, str, str]) -> str:
    start, end, fraction = (
        (palette[0], palette[1], value * 2)
        if value <= 0.5
        else (palette[1], palette[2], (value - 0.5) * 2)
    )
    return _blend(start, end, fraction)


def _blend(background: str, foreground: str, opacity: float) -> str:
    first = tuple(int(background[index : index + 2], 16) for index in (1, 3, 5))
    second = tuple(int(foreground[index : index + 2], 16) for index in (1, 3, 5))
    return "#" + "".join(
        f"{round(left * (1 - opacity) + right * opacity):02X}"
        for left, right in zip(first, second, strict=True)
    )

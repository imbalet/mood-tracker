from datetime import date
from io import BytesIO
from uuid import uuid4

from PIL import Image

from mood_tracker.application.commands import MonthCalendar
from mood_tracker.domain.entities import FieldDisplayConfig, ReferenceDays, StatePalette
from mood_tracker.domain.enums import DayStatus
from mood_tracker.presentation.rendering.calendar.month import (
    MonthCalendarImageService,
    MonthCalendarMapper,
    MonthCalendarRequest,
    _to_visualization_data,
)
from mood_tracker.presentation.rendering.calendar.renderer import (
    CalendarRenderer,
    Config,
    DayInfo,
    DayNumber,
    Emoji,
)
from mood_tracker.presentation.rendering.calendar.theme import CalendarTheme


def test_month_calendar_renders_a_png_with_state_color(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(
        is_core=True,
        minimum=0,
        maximum=2,
        display_config=FieldDisplayConfig(
            state_palette=StatePalette("#112233", "#445566", "#778899")
        ),
    )
    day = day_factory.build(day_date=date(2025, 2, 3), status=DayStatus.COMPLETE)
    day.save_value(state.current_version, 0)

    image_file = MonthCalendarImageService().render(
        MonthCalendar(date(2025, 2, 1), (day,), (state,), None)
    )
    opened = Image.open(BytesIO(image_file.data))

    assert opened.format == "PNG"
    assert (17, 34, 51) in opened.convert("RGB").get_flattened_data()


def test_mapper_builds_visual_info_for_every_day_of_the_month(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(is_core=True)
    day = day_factory.build(day_date=date(2025, 2, 3))
    source = MonthCalendar(date(2025, 2, 1), (day,), (state,), None)
    theme = CalendarTheme.default()

    result = MonthCalendarMapper(theme, len(theme.renderer.emoji.positions)).map(
        MonthCalendarRequest(source.month, _to_visualization_data(source))
    )

    assert set(result) == set(range(1, 29))


def test_current_best_and_worst_on_one_day_do_not_draw_a_record_border(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(is_core=True)
    day = day_factory.build(day_date=date(2025, 2, 3))
    source = MonthCalendar(
        date(2025, 2, 1),
        (day,),
        (state,),
        ReferenceDays(uuid4(), best_day_id=day.id, worst_day_id=day.id),
    )
    theme = CalendarTheme.default()

    result = MonthCalendarMapper(theme, len(theme.renderer.emoji.positions)).map(
        MonthCalendarRequest(source.month, _to_visualization_data(source))
    )

    assert result[3].border_color is None


def test_field_emoji_keeps_its_slot_when_an_earlier_field_is_empty(
    day_factory, field_factory
) -> None:
    hydration = field_factory.ordinal(
        sort_order=0,
        display_config=FieldDisplayConfig(emoji="A"),
    )
    exercise = field_factory.ordinal(
        sort_order=1,
        display_config=FieldDisplayConfig(emoji="B"),
    )
    day = day_factory.build(day_date=date(2025, 2, 3))
    day.save_value(hydration.current_version, 0)
    day.save_value(exercise.current_version, 2)
    source = MonthCalendar(date(2025, 2, 1), (day,), (hydration, exercise), None)
    theme = CalendarTheme.default()

    result = MonthCalendarMapper(theme, len(theme.renderer.emoji.positions)).map(
        MonthCalendarRequest(source.month, _to_visualization_data(source))
    )

    assert result[3].emojis == (None, "B")


def test_renderer_keeps_day_number_and_emoji_grid_configuration() -> None:
    renderer = CalendarRenderer(
        Config(
            day_number=DayNumber(position=(2, 0)),
            emoji=Emoji(positions=((0, 1), (2, 2)), gap=3),
        )
    )
    day_data = {day: DayInfo() for day in range(1, 29)}
    day_data[1] = DayInfo(dot_color="#336699", dot_style="hatched", emojis=("A", "B"))

    image = Image.open(
        BytesIO(renderer.render_calendar(year=2025, month=2, day_data=day_data))
    )

    assert image.format == "PNG"

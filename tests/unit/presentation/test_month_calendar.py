from datetime import date
from io import BytesIO

from PIL import Image

from mood_tracker.application.commands import MonthCalendar
from mood_tracker.domain.entities import FieldDisplayConfig, StatePalette
from mood_tracker.domain.enums import DayStatus
from mood_tracker.presentation.month_calendar import _marker_size, render_month_calendar


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

    image_file = render_month_calendar(
        MonthCalendar(date(2025, 2, 1), (day,), (state,))
    )
    opened = Image.open(BytesIO(image_file.data))

    assert opened.format == "PNG"
    assert (17, 34, 51) in opened.convert("RGB").get_flattened_data()


def test_ordinal_marker_size_is_interpolated_from_its_normalized_value() -> None:
    assert _marker_size(0.0) == 14
    assert _marker_size(0.5) == 21
    assert _marker_size(1.0) == 28

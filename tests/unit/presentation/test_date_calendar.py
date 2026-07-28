from datetime import date

from aiogram_calendar.schemas import SimpleCalendarCallback

from mood_tracker.domain.enums import DayStatus
from mood_tracker.presentation.date_calendar import MoodDateCalendar


async def test_date_calendar_marks_complete_and_draft_days() -> None:
    calendar = MoodDateCalendar(
        date(2025, 2, 20),
        {date(2025, 2, 3): DayStatus.COMPLETE, date(2025, 2, 4): DayStatus.DRAFT},
    )

    markup = await calendar.start_calendar(2025, 2)
    labels = [button.text for row in markup.inline_keyboard for button in row]

    assert "✅ 3" in labels
    assert "📝 4" in labels
    assert "20" in labels
    selected = next(
        button
        for row in markup.inline_keyboard
        for button in row
        if button.text == "✅ 3"
    )
    callback = SimpleCalendarCallback.unpack(selected.callback_data)
    assert callback.year == 2025
    assert callback.month == 2
    assert callback.day == 3

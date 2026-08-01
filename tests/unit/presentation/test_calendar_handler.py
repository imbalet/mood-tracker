from datetime import date
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from aiogram.types import BufferedInputFile

from mood_tracker.application.commands import MonthCalendar
from mood_tracker.presentation.handlers.calendar import _month_image
from mood_tracker.presentation.rendering.calendar import MonthCalendarImageService
from mood_tracker.presentation.services import ApplicationServices


@pytest.mark.asyncio
async def test_month_image_handler_reads_calendar_and_uses_injected_renderer() -> None:
    user_id = uuid4()
    month = date(2025, 2, 1)
    data = MonthCalendar(month, (), (), None)
    use_case = SimpleNamespace(execute=AsyncMock(return_value=data))
    services = cast(
        ApplicationServices,
        SimpleNamespace(get_month_calendar=Mock(return_value=use_case)),
    )
    expected = BufferedInputFile(b"png", filename="calendar.png")
    render = Mock(return_value=expected)
    calendar_images = cast(
        MonthCalendarImageService,
        SimpleNamespace(render=render),
    )

    result = await _month_image(user_id, month, services, calendar_images)

    assert result is expected
    use_case.execute.assert_awaited_once()
    render.assert_called_once_with(data)

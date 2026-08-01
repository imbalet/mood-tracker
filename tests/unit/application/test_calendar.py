from datetime import date
from unittest.mock import AsyncMock

from mood_tracker.application.commands import GetMonthCalendar
from mood_tracker.application.use_cases import GetMonthCalendarUseCase


async def test_month_calendar_reads_only_owned_month_data(
    uow, user_factory, day_factory, field_factory
) -> None:
    user = user_factory.build()
    day = day_factory.build(user_id=user.id, day_date=date(2025, 2, 3))
    state = field_factory.scale(user_id=user.id, is_core=True)
    uow.users.get = AsyncMock(return_value=user)
    uow.days.list_for_month = AsyncMock(return_value=[day])
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.reference_days.get = AsyncMock(return_value=None)

    result = await GetMonthCalendarUseCase(uow).execute(
        GetMonthCalendar(user.id, date(2025, 2, 20))
    )

    assert result.month == date(2025, 2, 1)
    assert result.days == (day,)
    assert result.fields == (state,)
    assert result.references is None
    uow.days.list_for_month.assert_awaited_once_with(user.id, date(2025, 2, 1))
    uow.reference_days.get.assert_awaited_once_with(user.id)

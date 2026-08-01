from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from mood_tracker.application.commands import (
    ChangeEventTime,
    CompleteEvent,
    CreateEvent,
    CreateQuickEvent,
    SaveEventValue,
)
from mood_tracker.application.use_cases.events import (
    ChangeEventTimeUseCase,
    CompleteEventUseCase,
    CreateEventUseCase,
    CreateQuickEventUseCase,
    SaveEventValueUseCase,
)
from mood_tracker.domain.errors import InvalidFieldValue


async def test_quick_event_saves_text_as_a_draft(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    description = field_factory.text(user_id=user.id, name="Описание")
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.list_for_user = AsyncMock(return_value=[description])
    use_case = CreateQuickEventUseCase(uow, clock, id_generator)

    event = await use_case.execute(CreateQuickEvent(user.id, "Важная мысль"))

    assert event.occurred_timezone == user.timezone.name
    assert event.values[description.id].value == "Важная мысль"
    uow.events.add.assert_awaited_once_with(event)


async def test_quick_event_rejects_blank_text(
    uow, clock, id_generator, user_factory
) -> None:
    user = user_factory.build()
    uow.users.get = AsyncMock(return_value=user)
    use_case = CreateQuickEventUseCase(uow, clock, id_generator)

    with pytest.raises(InvalidFieldValue):
        await use_case.execute(CreateQuickEvent(user.id, "  "))

    uow.events.add.assert_not_awaited()


async def test_regular_event_saves_value_completes_and_changes_time(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id, name="Описание")
    occurred_at = datetime(2025, 1, 2, 9, 0, tzinfo=UTC)
    uow.users.get = AsyncMock(return_value=user)
    event = await CreateEventUseCase(uow, id_generator).execute(
        CreateEvent(user.id, occurred_at, user.timezone.name)
    )
    uow.events.get = AsyncMock(return_value=event)
    uow.fields.list_for_user = AsyncMock(return_value=[field])

    saved = await SaveEventValueUseCase(uow).execute(
        SaveEventValue(user.id, event.id, field.id, "Важная мысль")
    )
    completed = await CompleteEventUseCase(uow, clock).execute(
        CompleteEvent(user.id, event.id)
    )
    changed = await ChangeEventTimeUseCase(uow).execute(
        ChangeEventTime(user.id, event.id, datetime(2025, 1, 2, 10, 0, tzinfo=UTC))
    )

    assert saved.values[field.id].value == "Важная мысль"
    assert completed.completed_at == clock.now()
    assert changed.occurred_at == datetime(2025, 1, 2, 10, 0, tzinfo=UTC)

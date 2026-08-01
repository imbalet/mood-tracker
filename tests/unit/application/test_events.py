from unittest.mock import AsyncMock

import pytest

from mood_tracker.application.commands import CreateQuickEvent
from mood_tracker.application.use_cases.events import CreateQuickEventUseCase
from mood_tracker.domain.entities import EventFieldConfig
from mood_tracker.domain.errors import InvalidFieldValue


async def test_quick_event_saves_text_as_a_draft(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    description = field_factory.text(user_id=user.id, name="Описание")
    description.event_config = EventFieldConfig(False, 0, is_system=True)
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

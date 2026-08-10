from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid7

import pytest

from mood_tracker.application.commands import (
    ChangeEventTime,
    CompleteEvent,
    CreateEvent,
    CreateQuickEvent,
    SaveEventValue,
)
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.application.use_cases.events import (
    ChangeEventTimeUseCase,
    CompleteEventUseCase,
    CreateEventUseCase,
    CreateQuickEventUseCase,
    SaveEventValueUseCase,
)
from mood_tracker.domain.entities import Event, Questionnaire
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.domain.errors import InvalidFieldValue, InvalidTimestamp


async def test_quick_event_saves_text_as_a_draft(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    description = field_factory.text(user_id=user.id, name="Описание")
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.list_for_user = AsyncMock(return_value=[description])
    use_case = CreateQuickEventUseCase(uow, clock, id_generator)

    event = await use_case.execute(CreateQuickEvent(user.id, "Важная мысль"))

    assert event.occurred_timezone == user.timezone
    assert event.response.answers[description.id].value == "Важная мысль"
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
    uow.fields.list_for_user = AsyncMock(return_value=[field])
    event = await CreateEventUseCase(uow, id_generator).execute(
        CreateEvent(user.id, occurred_at, user.timezone)
    )
    uow.events.get = AsyncMock(return_value=event)

    assert event.response.answers == {}

    saved = await SaveEventValueUseCase(uow).execute(
        SaveEventValue(user.id, event.id, field.id, "Важная мысль")
    )
    completed = await CompleteEventUseCase(uow, clock).execute(
        CompleteEvent(user.id, event.id)
    )
    changed = await ChangeEventTimeUseCase(uow).execute(
        ChangeEventTime(
            user.id,
            event.id,
            datetime(2025, 1, 2, 13, 0, tzinfo=timezone(timedelta(hours=3))),
        )
    )

    assert saved.response.answers[field.id].value == "Важная мысль"
    assert completed.completed_at == clock.now()
    assert changed.occurred_at == datetime(2025, 1, 2, 10, 0, tzinfo=UTC)


async def test_create_event_normalizes_aware_time_to_utc(
    uow, id_generator, user_factory
) -> None:
    user = user_factory.build()
    uow.users.get = AsyncMock(return_value=user)
    local_time = datetime(2025, 1, 2, 12, 0, tzinfo=timezone(timedelta(hours=3)))

    event = await CreateEventUseCase(uow, id_generator).execute(
        CreateEvent(user.id, local_time, user.timezone)
    )

    assert event.occurred_at == datetime(2025, 1, 2, 9, 0, tzinfo=UTC)


async def test_create_event_rejects_naive_time(uow, id_generator, user_factory) -> None:
    user = user_factory.build()
    uow.users.get = AsyncMock(return_value=user)

    with pytest.raises(InvalidFieldValue):
        await CreateEventUseCase(uow, id_generator).execute(
            CreateEvent(user.id, datetime(2025, 1, 2, 12, 0), user.timezone)
        )


def test_event_rejects_non_utc_domain_time(user_factory) -> None:
    user = user_factory.build()

    with pytest.raises(InvalidTimestamp):
        Event(
            id=uuid7(),
            user_id=user.id,
            occurred_at=datetime(
                2025, 1, 2, 12, 0, tzinfo=timezone(timedelta(hours=3))
            ),
            occurred_timezone=user.timezone,
        )


async def test_event_uses_current_questionnaire_placements(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id, name="Описание")
    event = Event(
        id=uuid7(),
        user_id=user.id,
        occurred_at=datetime(2025, 1, 2, 9, 0, tzinfo=UTC),
        occurred_timezone=user.timezone,
    )
    questionnaire = Questionnaire(
        id=uuid7(),
        user_id=user.id,
        kind=QuestionnaireKind.EVENT,
        fields={field.id: QuestionnaireField(field.id, 0)},
    )
    uow.events.get = AsyncMock(return_value=event)
    uow.fields.list_for_user = AsyncMock(return_value=[field])
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)
    use_case = SaveEventValueUseCase(uow)

    await use_case.execute(SaveEventValue(user.id, event.id, field.id, "Текст"))
    del questionnaire.fields[field.id]

    with pytest.raises(FieldNotFound):
        await use_case.execute(SaveEventValue(user.id, event.id, field.id, "Ещё текст"))

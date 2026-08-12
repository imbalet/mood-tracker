from datetime import date
from unittest.mock import AsyncMock

import pytest

from mood_tracker.application.contracts.diary import GetDay, SaveDayValue, SkipDayText
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.application.use_cases import (
    GetDayUseCase,
    SaveDayValueUseCase,
    SkipDayTextUseCase,
)
from mood_tracker.domain.entities import Questionnaire
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import DayStatus, QuestionnaireKind


async def test_get_empty_day_does_not_create_draft(
    uow, clock, user_factory, field_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    uow.users.get = AsyncMock(return_value=user)
    uow.days.get_by_date = AsyncMock(return_value=None)
    uow.fields.list_for_user = AsyncMock(return_value=[state])

    form = await GetDayUseCase(uow, clock).execute(GetDay(user.id, date(2025, 1, 2)))

    assert form.day is None
    assert form.next_field == state
    uow.days.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_save_first_core_value_creates_day_and_reference_baselines(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=state)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_by_date = AsyncMock(return_value=None)
    uow.reference_days.get = AsyncMock(return_value=None)
    use_case = SaveDayValueUseCase(uow, clock, id_generator)

    review = await use_case.execute(
        SaveDayValue(user.id, date(2025, 1, 2), state.id, 5)
    )

    day = uow.days.add.await_args.args[0]
    references = uow.reference_days.save.await_args.args[0]
    assert review is None
    assert day.response.answers[state.id].value == 5
    assert day.status is DayStatus.COMPLETE
    assert references.best_day_id == day.id
    assert references.worst_day_id == day.id


async def test_skip_text_creates_and_completes_day(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    text = field_factory.text(user_id=user.id)
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=text)
    uow.fields.list_for_user = AsyncMock(return_value=[text])
    uow.days.get_by_date = AsyncMock(return_value=None)

    await SkipDayTextUseCase(uow, clock, id_generator).execute(
        SkipDayText(user.id, date(2025, 1, 2), text.id)
    )

    day = uow.days.add.await_args.args[0]
    assert day.status is DayStatus.COMPLETE
    assert day.response.progress[text.id].skipped


async def test_save_day_value_rejects_disabled_questionnaire_field(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.scale(user_id=user.id)
    questionnaire = Questionnaire(
        id=id_generator.new(),
        user_id=user.id,
        kind=QuestionnaireKind.DAY,
        fields={field.id: QuestionnaireField(field.id, 0, is_enabled=False)},
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    with pytest.raises(FieldNotFound):
        await SaveDayValueUseCase(uow, clock, id_generator).execute(
            SaveDayValue(user.id, date(2025, 1, 2), field.id, 3)
        )

    uow.days.add.assert_not_awaited()


async def test_skip_day_text_rejects_detached_questionnaire_field(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    questionnaire = Questionnaire(
        id=id_generator.new(),
        user_id=user.id,
        kind=QuestionnaireKind.DAY,
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)
    uow.fields.get = AsyncMock(return_value=field)

    with pytest.raises(FieldNotFound):
        await SkipDayTextUseCase(uow, clock, id_generator).execute(
            SkipDayText(user.id, date(2025, 1, 2), field.id)
        )

    uow.days.add.assert_not_awaited()

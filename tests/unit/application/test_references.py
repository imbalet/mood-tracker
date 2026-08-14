from datetime import date
from unittest.mock import AsyncMock

import pytest

from mood_tracker.application.contracts.diary import ConfirmReference, SaveDayValue
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.application.use_cases import (
    ConfirmReferenceUseCase,
    SaveDayValueUseCase,
)
from mood_tracker.domain.entities import Questionnaire, ReferenceDays
from mood_tracker.domain.enums import QuestionnaireKind, ReferenceType


async def test_boundary_value_requests_confirmation_against_existing_reference(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    old_day = day_factory.build(user_id=user.id)
    old_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        old_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=state)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_by_date = AsyncMock(return_value=None)
    uow.days.get_many = AsyncMock(return_value=[old_day])
    uow.reference_days.get = AsyncMock(return_value=references)

    review = await SaveDayValueUseCase(uow, clock, id_generator).execute(
        SaveDayValue(user.id, date(2025, 1, 2), state.id, 0)
    )

    assert review is not None
    assert review.type is ReferenceType.WORST
    assert review.previous_reference_day_id == old_day.id


async def test_boundary_value_becomes_reference_when_previous_history_is_not_valid(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    old_day = day_factory.build(user_id=user.id)
    old_day.save_value(state.current_version, 5)
    references = ReferenceDays(user.id)
    references.initialize(
        old_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=state)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_by_date = AsyncMock(return_value=None)
    uow.days.get_many = AsyncMock(return_value=[old_day])
    uow.reference_days.get = AsyncMock(return_value=references)

    review = await SaveDayValueUseCase(uow, clock, id_generator).execute(
        SaveDayValue(user.id, date(2025, 1, 2), state.id, 0)
    )

    new_day = uow.days.add.await_args.args[0]
    assert review is None
    assert references.worst_day_id == new_day.id


async def test_confirm_reference_appends_history_entry(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    old_day = day_factory.build(user_id=user.id)
    new_day = day_factory.build(user_id=user.id)
    new_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        old_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.days.get = AsyncMock(return_value=new_day)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.reference_days.get = AsyncMock(return_value=references)

    await ConfirmReferenceUseCase(uow, clock, id_generator).execute(
        ConfirmReference(user.id, new_day.id, ReferenceType.WORST, True)
    )

    assert references.worst_day_id == new_day.id
    assert references.history[-1].previous_reference_day_id == old_day.id


async def test_editing_current_reference_rolls_back_to_previous_valid_day(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    previous_day = day_factory.build(user_id=user.id, day_date=date(2025, 1, 1))
    current_day = day_factory.build(user_id=user.id, day_date=date(2025, 1, 2))
    previous_day.save_value(state.current_version, 0)
    current_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        previous_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    references.apply_confirmed_change(
        id_generator.new(), current_day.id, ReferenceType.WORST, clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=state)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_by_date = AsyncMock(return_value=current_day)
    uow.days.get_many = AsyncMock(return_value=[previous_day, current_day])
    uow.reference_days.get = AsyncMock(return_value=references)

    review = await SaveDayValueUseCase(uow, clock, id_generator).execute(
        SaveDayValue(user.id, current_day.date, state.id, 3)
    )

    assert review is None
    assert references.worst_day_id == previous_day.id


async def test_state_save_loads_reference_history_once_and_persists_one_update(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    previous_day = day_factory.build(user_id=user.id, day_date=date(2025, 1, 1))
    current_day = day_factory.build(user_id=user.id, day_date=date(2025, 1, 2))
    previous_day.save_value(state.current_version, 0)
    current_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        previous_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    references.apply_confirmed_change(
        id_generator.new(), current_day.id, ReferenceType.WORST, clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.get = AsyncMock(return_value=state)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_by_date = AsyncMock(return_value=current_day)
    uow.days.get_many = AsyncMock(return_value=[previous_day, current_day])
    uow.reference_days.get = AsyncMock(return_value=references)

    review = await SaveDayValueUseCase(uow, clock, id_generator).execute(
        SaveDayValue(user.id, current_day.date, state.id, 10)
    )

    assert review is not None
    assert references.worst_day_id == previous_day.id
    uow.days.get_many.assert_awaited_once()
    uow.reference_days.save.assert_awaited_once_with(references)


async def test_rejected_reference_restores_previous_valid_day(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    previous_day = day_factory.build(user_id=user.id)
    current_day = day_factory.build(user_id=user.id)
    previous_day.save_value(state.current_version, 0)
    current_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        previous_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    references.apply_confirmed_change(
        id_generator.new(), current_day.id, ReferenceType.WORST, clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.days.get = AsyncMock(return_value=current_day)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.days.get_many = AsyncMock(return_value=[previous_day, current_day])
    uow.reference_days.get = AsyncMock(return_value=references)

    await ConfirmReferenceUseCase(uow, clock, id_generator).execute(
        ConfirmReference(user.id, current_day.id, ReferenceType.WORST, False)
    )

    assert references.worst_day_id == previous_day.id


async def test_repeated_reference_confirmation_does_not_append_duplicates(
    uow, clock, id_generator, user_factory, field_factory, day_factory
) -> None:
    user = user_factory.build()
    state = field_factory.scale(user_id=user.id, is_core=True)
    previous_day = day_factory.build(user_id=user.id)
    new_day = day_factory.build(user_id=user.id)
    new_day.save_value(state.current_version, 0)
    references = ReferenceDays(user.id)
    references.initialize(
        previous_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.days.get = AsyncMock(return_value=new_day)
    uow.fields.list_for_user = AsyncMock(return_value=[state])
    uow.reference_days.get = AsyncMock(return_value=references)
    use_case = ConfirmReferenceUseCase(uow, clock, id_generator)

    command = ConfirmReference(user.id, new_day.id, ReferenceType.WORST, True)
    await use_case.execute(command)
    await use_case.execute(command)

    assert references.worst_day_id == new_day.id
    assert len(references.history) == 3
    uow.reference_days.save.assert_awaited_once_with(references)


async def test_confirm_reference_reports_missing_state_system_field(
    uow, clock, id_generator, user_factory, day_factory
) -> None:
    user = user_factory.build()
    day = day_factory.build(user_id=user.id)
    questionnaire = Questionnaire(
        id=id_generator.new(), user_id=user.id, kind=QuestionnaireKind.DAY
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.days.get = AsyncMock(return_value=day)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)
    uow.fields.list_for_user = AsyncMock(return_value=[])

    with pytest.raises(FieldNotFound):
        await ConfirmReferenceUseCase(uow, clock, id_generator).execute(
            ConfirmReference(user.id, day.id, ReferenceType.WORST, True)
        )

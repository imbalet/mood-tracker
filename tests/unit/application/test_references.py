from datetime import date
from unittest.mock import AsyncMock

from mood_tracker.application.commands import ConfirmReference, SaveDayValue
from mood_tracker.application.use_cases import (
    ConfirmReferenceUseCase,
    SaveDayValueUseCase,
)
from mood_tracker.domain.entities import ReferenceDays
from mood_tracker.domain.enums import ReferenceType


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


async def test_first_boundary_value_becomes_reference_without_confirmation(
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

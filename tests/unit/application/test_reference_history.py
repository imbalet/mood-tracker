from unittest.mock import AsyncMock

from mood_tracker.application.contracts.references import GetReferenceHistory
from mood_tracker.application.use_cases import GetReferenceHistoryUseCase
from mood_tracker.domain.entities import ReferenceDays
from mood_tracker.domain.enums import ReferenceType


async def test_reference_history_separates_active_chain_from_audit_events(
    uow, clock, id_generator, user_factory, day_factory
) -> None:
    user = user_factory.build()
    first_day = day_factory.build(user_id=user.id)
    retracted_day = day_factory.build(user_id=user.id)
    reference_days = ReferenceDays(user.id)
    reference_days.initialize(
        first_day.id, id_generator.new(), id_generator.new(), clock.now()
    )
    reference_days.apply_confirmed_change(
        id_generator.new(), retracted_day.id, ReferenceType.WORST, clock.now()
    )
    reference_days.rollback_current(
        ReferenceType.WORST, lambda day_id: day_id == first_day.id
    )
    uow.users.get = AsyncMock(return_value=user)
    uow.reference_days.get = AsyncMock(return_value=reference_days)

    history = await GetReferenceHistoryUseCase(uow).execute(
        GetReferenceHistory(user.id)
    )

    assert [event.day_id for event in history.worst_chain] == [first_day.id]
    assert retracted_day.id in {event.day_id for event in history.all_events}

"""Read models for current and historical reference-day views."""

from mood_tracker.application.contracts.references import (
    GetReferenceHistory,
    ReferenceHistory,
)
from mood_tracker.application.errors import UserNotFound
from mood_tracker.application.ports import UnitOfWork
from mood_tracker.domain.entities import ReferenceDay, ReferenceDays
from mood_tracker.domain.enums import ReferenceType


def _active_chain(
    reference_days: ReferenceDays, type: ReferenceType
) -> tuple[ReferenceDay, ...]:
    current_day_id = (
        reference_days.best_day_id
        if type is ReferenceType.BEST
        else reference_days.worst_day_id
    )
    chain: list[ReferenceDay] = []
    while current_day_id is not None:
        reference = next(
            (
                event
                for event in reversed(reference_days.history)
                if event.type is type and event.day_id == current_day_id
            ),
            None,
        )
        if reference is None:
            break
        chain.append(reference)
        current_day_id = reference.previous_reference_day_id
    return tuple(reversed(chain))


class GetReferenceHistoryUseCase:
    """Expose active chains separately from the immutable audit journal."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetReferenceHistory) -> ReferenceHistory:
        """Return an empty history for a user without any state values yet."""
        async with self._uow:
            if await self._uow.users.get(command.user_id) is None:
                raise UserNotFound
            reference_days = await self._uow.reference_days.get(command.user_id)
            if reference_days is None:
                return ReferenceHistory((), (), ())
            return ReferenceHistory(
                best_chain=_active_chain(reference_days, ReferenceType.BEST),
                worst_chain=_active_chain(reference_days, ReferenceType.WORST),
                all_events=tuple(reference_days.history),
            )

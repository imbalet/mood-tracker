"""Current reference-state and immutable history repository."""

from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.application.ports import ReferenceDaysRepository
from mood_tracker.domain.entities import ReferenceDay, ReferenceDays
from mood_tracker.domain.enums import ReferenceType
from mood_tracker.infrastructure.db.models import DayReferenceOrm, ReferenceStateOrm


class SqlAlchemyReferenceDaysRepository(ReferenceDaysRepository):
    """Persist current best/worst pointers and append-only reference history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get(self, user_id: UUID) -> ReferenceDays | None:
        state = await self._session.get(ReferenceStateOrm, user_id)
        if state is None:
            return None
        rows = (
            await self._session.scalars(
                select(DayReferenceOrm)
                .where(DayReferenceOrm.user_id == user_id)
                .order_by(DayReferenceOrm.created_at)
            )
        ).all()
        return ReferenceDays(
            user_id,
            state.best_day_id,
            state.worst_day_id,
            [
                ReferenceDay(
                    row.id,
                    row.user_id,
                    row.day_id,
                    ReferenceType(row.type),
                    row.previous_reference_day_id,
                    row.created_at,
                )
                for row in rows
            ],
        )

    @override
    async def save(self, reference_days: ReferenceDays) -> None:
        state = await self._session.get(ReferenceStateOrm, reference_days.user_id)
        if state is None:
            self._session.add(
                ReferenceStateOrm(
                    user_id=reference_days.user_id,
                    best_day_id=reference_days.best_day_id,
                    worst_day_id=reference_days.worst_day_id,
                )
            )
        else:
            state.best_day_id, state.worst_day_id = (
                reference_days.best_day_id,
                reference_days.worst_day_id,
            )
        existing_ids = set(
            (
                await self._session.scalars(
                    select(DayReferenceOrm.id).where(
                        DayReferenceOrm.user_id == reference_days.user_id
                    )
                )
            ).all()
        )
        for reference in reference_days.history:
            if reference.id not in existing_ids:
                self._session.add(
                    DayReferenceOrm(
                        id=reference.id,
                        user_id=reference.user_id,
                        day_id=reference.day_id,
                        type=reference.type.value,
                        previous_reference_day_id=reference.previous_reference_day_id,
                        created_at=reference.created_at,
                    )
                )

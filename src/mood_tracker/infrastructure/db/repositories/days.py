"""Day, value and questionnaire-progress repository."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.domain.entities import Day, DayFieldProgress, DayValue
from mood_tracker.domain.enums import DayStatus
from mood_tracker.infrastructure.db.models import (
    DayFieldProgressOrm,
    DayOrm,
    DayValueOrm,
)


class SqlAlchemyDayRepository:
    """Persist daily entries and their current answers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, day_id: UUID) -> Day | None:
        row = await self._session.scalar(
            select(DayOrm).where(DayOrm.id == day_id, DayOrm.user_id == user_id)
        )
        return await self._to_domain(row) if row else None

    async def get_by_date(self, user_id: UUID, day_date: date) -> Day | None:
        row = await self._session.scalar(
            select(DayOrm).where(DayOrm.user_id == user_id, DayOrm.date == day_date)
        )
        return await self._to_domain(row) if row else None

    async def get_many(self, user_id: UUID, day_ids: Sequence[UUID]) -> Sequence[Day]:
        if not day_ids:
            return []
        rows = (
            await self._session.scalars(
                select(DayOrm).where(DayOrm.user_id == user_id, DayOrm.id.in_(day_ids))
            )
        ).all()
        return [await self._to_domain(row) for row in rows]

    async def add(self, day: Day) -> None:
        self._session.add(
            DayOrm(
                id=day.id,
                user_id=day.user_id,
                date=day.date,
                status=day.status.value,
                completed_at=day.completed_at,
            )
        )
        await self._replace_children(day)

    async def save(self, day: Day) -> None:
        row = await self._session.get(DayOrm, day.id)
        if row is not None:
            row.status, row.completed_at = day.status.value, day.completed_at
        await self._replace_children(day)

    async def _replace_children(self, day: Day) -> None:
        await self._session.execute(
            delete(DayValueOrm).where(DayValueOrm.day_id == day.id)
        )
        await self._session.execute(
            delete(DayFieldProgressOrm).where(DayFieldProgressOrm.day_id == day.id)
        )
        for value in day.values.values():
            self._session.add(
                DayValueOrm(
                    id=uuid7(),
                    day_id=day.id,
                    field_id=value.field_id,
                    field_version_id=value.field_version_id,
                    value={"value": value.value},
                    normalized_value=(
                        Decimal(str(value.normalized_value))
                        if value.normalized_value is not None
                        else None
                    ),
                )
            )
        for progress in day.progress.values():
            self._session.add(
                DayFieldProgressOrm(
                    id=uuid7(),
                    day_id=day.id,
                    field_id=progress.field_id,
                    field_version_id=progress.field_version_id,
                    skipped=progress.skipped,
                )
            )

    async def _to_domain(self, row: DayOrm) -> Day:
        value_rows = (
            await self._session.scalars(
                select(DayValueOrm).where(DayValueOrm.day_id == row.id)
            )
        ).all()
        progress_rows = (
            await self._session.scalars(
                select(DayFieldProgressOrm).where(DayFieldProgressOrm.day_id == row.id)
            )
        ).all()
        return Day(
            row.id,
            row.user_id,
            row.date,
            DayStatus(row.status),
            row.completed_at,
            {
                value.field_id: DayValue(
                    row.id,
                    value.field_id,
                    value.field_version_id,
                    value.value["value"],
                    (
                        float(value.normalized_value)
                        if value.normalized_value is not None
                        else None
                    ),
                )
                for value in value_rows
            },
            {
                progress.field_id: DayFieldProgress(
                    progress.field_id,
                    progress.field_version_id,
                    progress.skipped,
                )
                for progress in progress_rows
            },
        )


__all__ = ["SqlAlchemyDayRepository"]

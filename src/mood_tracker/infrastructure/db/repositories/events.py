"""Event repository with owner-scoped reads and soft deletion."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid7
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.domain.entities import (
    Answer,
    Event,
    QuestionnaireResponse,
    QuestionProgress,
)
from mood_tracker.domain.enums import EventStatus
from mood_tracker.domain.value_objects import UserTimezone
from mood_tracker.infrastructure.db.models import (
    EventFieldProgressOrm,
    EventOrm,
    EventValueOrm,
)


class SqlAlchemyEventRepository:
    """Persist standalone contextual events for exactly one owner."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, event_id: UUID) -> Event | None:
        row = await self._session.scalar(
            select(EventOrm).where(
                EventOrm.id == event_id,
                EventOrm.user_id == user_id,
                EventOrm.deleted_at.is_(None),
            )
        )
        return await self._to_domain(row) if row else None

    async def list_for_date(self, user_id: UUID, event_date: date) -> Sequence[Event]:
        rows = (
            await self._session.scalars(
                select(EventOrm)
                .where(EventOrm.user_id == user_id, EventOrm.deleted_at.is_(None))
                .order_by(EventOrm.occurred_at)
            )
        ).all()
        return [
            await self._to_domain(row)
            for row in rows
            if row.occurred_at.astimezone(ZoneInfo(row.occurred_timezone)).date()
            == event_date
        ]

    async def add(self, event: Event) -> None:
        self._session.add(
            EventOrm(
                id=event.id,
                user_id=event.user_id,
                occurred_at=event.occurred_at,
                occurred_timezone=event.occurred_timezone.name,
                status=event.status.value,
                completed_at=event.completed_at,
                deleted_at=event.deleted_at,
            )
        )
        await self._replace_children(event)

    async def save(self, event: Event) -> None:
        row = await self._session.get(EventOrm, event.id)
        if row is not None:
            (
                row.occurred_at,
                row.occurred_timezone,
                row.status,
                row.completed_at,
                row.deleted_at,
            ) = (
                event.occurred_at,
                event.occurred_timezone.name,
                event.status.value,
                event.completed_at,
                event.deleted_at,
            )
        await self._replace_children(event)

    async def _replace_children(self, event: Event) -> None:
        await self._session.execute(
            delete(EventValueOrm).where(EventValueOrm.event_id == event.id)
        )
        await self._session.execute(
            delete(EventFieldProgressOrm).where(
                EventFieldProgressOrm.event_id == event.id
            )
        )
        for value in event.response.answers.values():
            self._session.add(
                EventValueOrm(
                    id=uuid7(),
                    event_id=event.id,
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
        for progress in event.response.progress.values():
            self._session.add(
                EventFieldProgressOrm(
                    id=uuid7(),
                    event_id=event.id,
                    field_id=progress.field_id,
                    field_version_id=progress.field_version_id,
                    skipped=progress.skipped,
                )
            )

    async def _to_domain(self, row: EventOrm) -> Event:
        value_rows = (
            await self._session.scalars(
                select(EventValueOrm).where(EventValueOrm.event_id == row.id)
            )
        ).all()
        progress_rows = (
            await self._session.scalars(
                select(EventFieldProgressOrm).where(
                    EventFieldProgressOrm.event_id == row.id
                )
            )
        ).all()
        return Event(
            id=row.id,
            user_id=row.user_id,
            occurred_at=row.occurred_at,
            occurred_timezone=UserTimezone(row.occurred_timezone),
            status=EventStatus(row.status),
            completed_at=row.completed_at,
            deleted_at=row.deleted_at,
            response=QuestionnaireResponse(
                answers={
                    value.field_id: Answer(
                        field_id=value.field_id,
                        field_version_id=value.field_version_id,
                        value=value.value["value"],
                        normalized_value=float(value.normalized_value)
                        if value.normalized_value is not None
                        else None,
                    )
                    for value in value_rows
                },
                progress={
                    progress.field_id: QuestionProgress(
                        field_id=progress.field_id,
                        field_version_id=progress.field_version_id,
                        skipped=progress.skipped,
                    )
                    for progress in progress_rows
                },
            ),
        )


__all__ = ["SqlAlchemyEventRepository"]

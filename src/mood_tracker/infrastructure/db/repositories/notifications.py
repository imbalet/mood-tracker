"""User-profile repository."""

# TODO: посмотреть слоп

from datetime import UTC, date, datetime, timedelta
from typing import Any, cast, override
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.application.ports import (
    NotificationDeliveryRepository,
    NotificationSettingsRepository,
)
from mood_tracker.application.ports.repositories import (
    NotificationDelivery as NotificationDeliveryDTO,
)
from mood_tracker.application.ports.repositories import (
    NotificationDeliveryStatus,
)
from mood_tracker.domain.entities import NotificationSettings
from mood_tracker.infrastructure.db.models import (
    NotificationDeliveriesOrm,
    NotificationSettingsOrm,
)

# TODO: посмотреть слоп


class SqlAlchemyNotificationSettingsRepository(NotificationSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get(self, user_id: UUID) -> NotificationSettings | None:
        row = await self._session.get(NotificationSettingsOrm, user_id)
        return _to_domain(row) if row else None

    @override
    async def add(self, settings: NotificationSettings) -> None:
        self._session.add(
            NotificationSettingsOrm(
                user_id=settings.user_id,
                is_enabled=settings.is_enabled,
                reminder_time=settings.reminder_time,
                repeat_interval=settings.repeat_interval,
                max_reminders_per_day=settings.max_reminders_per_day,
            )
        )

    @override
    async def save(self, settings: NotificationSettings) -> None:
        row = await self._session.get(NotificationSettingsOrm, settings.user_id)
        if row:
            row.max_reminders_per_day = settings.max_reminders_per_day
            row.repeat_interval = settings.repeat_interval
            row.reminder_time = settings.reminder_time
            row.is_enabled = settings.is_enabled


def _to_domain(row: NotificationSettingsOrm) -> NotificationSettings:
    return NotificationSettings(
        user_id=row.user_id,
        is_enabled=row.is_enabled,
        reminder_time=row.reminder_time,
        repeat_interval=row.repeat_interval,
        max_reminders_per_day=row.max_reminders_per_day,
    )


class SqlAlchemyNotificationDeliveryRepository(NotificationDeliveryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get_deliveries(
        self,
        user_id: UUID,
        local_date: date,
    ) -> list[NotificationDeliveryDTO]:
        stmt = (
            select(
                NotificationDeliveriesOrm.reminder_number,
                NotificationDeliveriesOrm.status,
            )
            .where(
                NotificationDeliveriesOrm.user_id == user_id,
                NotificationDeliveriesOrm.local_date == local_date,
            )
            .order_by(NotificationDeliveriesOrm.reminder_number)
        )

        result = await self._session.execute(stmt)

        return [
            NotificationDeliveryDTO(
                reminder_number=reminder_number,
                status=NotificationDeliveryStatus(status),
            )
            for reminder_number, status in result.all()
        ]

    @override
    async def try_claim(
        self,
        user_id: UUID,
        local_date: date,
        reminder_number: int,
        claim_timeout: timedelta,
    ) -> bool:
        now = datetime.now(UTC)
        claimed_at = now - claim_timeout

        # 1. Если delivery ещё не существует — пытаемся создать её.
        insert_stmt = (
            insert(NotificationDeliveriesOrm)
            .values(
                user_id=user_id,
                local_date=local_date,
                reminder_number=reminder_number,
                status=NotificationDeliveryStatus.claimed.value,
                claimed_at=now,
                sent_at=None,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    NotificationDeliveriesOrm.user_id,
                    NotificationDeliveriesOrm.local_date,
                    NotificationDeliveriesOrm.reminder_number,
                ],
            )
        )

        result = await self._session.execute(insert_stmt)
        result = cast(CursorResult[Any], result)

        if result.rowcount == 1:
            return True

        # 2. Запись уже существует.
        # Пытаемся перехватить её, только если предыдущий claim протух.
        update_stmt = (
            update(NotificationDeliveriesOrm)
            .where(
                NotificationDeliveriesOrm.user_id == user_id,
                NotificationDeliveriesOrm.local_date == local_date,
                NotificationDeliveriesOrm.reminder_number == reminder_number,
                NotificationDeliveriesOrm.status
                == NotificationDeliveryStatus.claimed.value,
                NotificationDeliveriesOrm.claimed_at <= claimed_at,
            )
            .values(
                claimed_at=now,
            )
        )

        result = await self._session.execute(update_stmt)
        result = cast(CursorResult[Any], result)

        return result.rowcount == 1

    @override
    async def mark_sent(
        self,
        user_id: UUID,
        local_date: date,
        reminder_number: int,
        sent_at: datetime,
    ) -> None:
        stmt = (
            update(NotificationDeliveriesOrm)
            .where(
                NotificationDeliveriesOrm.user_id == user_id,
                NotificationDeliveriesOrm.local_date == local_date,
                NotificationDeliveriesOrm.reminder_number == reminder_number,
                NotificationDeliveriesOrm.status
                == NotificationDeliveryStatus.claimed.value,
            )
            .values(
                status=NotificationDeliveryStatus.sent.value,
                sent_at=sent_at,
            )
            .returning(NotificationDeliveriesOrm.user_id)
        )

        result = await self._session.execute(stmt)

        if result.scalar_one_or_none() is None:
            raise RuntimeError("Notification delivery was not claimed")

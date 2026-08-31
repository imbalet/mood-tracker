"""User-profile repository."""

from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.application.ports import UserRepository
from mood_tracker.domain.entities import UserProfile
from mood_tracker.domain.value_objects import UserTimezone
from mood_tracker.infrastructure.db.models import UserOrm


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get(self, user_id: UUID) -> UserProfile | None:
        row = await self._session.get(UserOrm, user_id)
        return _to_domain(row) if row else None

    @override
    async def get_by_telegram_id(self, telegram_id: int) -> UserProfile | None:
        row = await self._session.scalar(
            select(UserOrm).where(UserOrm.telegram_id == telegram_id)
        )
        return _to_domain(row) if row else None

    # TODO: посмотреть слоп
    @override
    async def list_all(self) -> list[UserProfile]:
        rows = (await self._session.scalars(select(UserOrm).order_by(UserOrm.id))).all()
        return [_to_domain(row) for row in rows]

    @override
    async def add(self, user: UserProfile) -> None:
        self._session.add(
            UserOrm(
                id=user.id, telegram_id=user.telegram_id, timezone=user.timezone.name
            )
        )

    @override
    async def save(self, user: UserProfile) -> None:
        row = await self._session.get(UserOrm, user.id)
        if row:
            row.timezone = user.timezone.name


def _to_domain(row: UserOrm) -> UserProfile:
    return UserProfile(row.id, row.telegram_id, UserTimezone(row.timezone))

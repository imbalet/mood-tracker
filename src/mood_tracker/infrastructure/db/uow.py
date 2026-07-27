"""SQLAlchemy transactional unit of work."""

from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mood_tracker.application.errors import IdentifierCollision
from mood_tracker.infrastructure.db.repositories import (
    SqlAlchemyDayRepository,
    SqlAlchemyFieldRepository,
    SqlAlchemyReferenceDaysRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.fields = SqlAlchemyFieldRepository(self._session)
        self.days = SqlAlchemyDayRepository(self._session)
        self.reference_days = SqlAlchemyReferenceDaysRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is not None:
            if exc_type:
                await self._session.rollback()
            await self._session.close()

    async def commit(self) -> None:
        session = self._session
        if session is None:
            msg = "Unit of work is not active"
            raise RuntimeError(msg)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise IdentifierCollision from error
            raise

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()

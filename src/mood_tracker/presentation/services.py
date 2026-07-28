"""Factories that bind application use cases to production adapters."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mood_tracker.application.use_cases import (
    ConfirmReferenceUseCase,
    GetDayUseCase,
    GetUserByTelegramIdUseCase,
    RegisterUserUseCase,
    SaveDayValueUseCase,
    SkipDayTextUseCase,
)
from mood_tracker.infrastructure.clock import SystemClock
from mood_tracker.infrastructure.db.uow import SqlAlchemyUnitOfWork
from mood_tracker.infrastructure.ids.uuid7 import Uuid7IdGenerator


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Create use cases with an isolated unit of work per Telegram update."""

    session_factory: async_sessionmaker[AsyncSession]

    def get_user_by_telegram_id(self) -> GetUserByTelegramIdUseCase:
        return GetUserByTelegramIdUseCase(self._uow())

    def register_user(self) -> RegisterUserUseCase:
        return RegisterUserUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def get_day(self) -> GetDayUseCase:
        return GetDayUseCase(self._uow(), SystemClock())

    def save_day_value(self) -> SaveDayValueUseCase:
        return SaveDayValueUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def skip_day_text(self) -> SkipDayTextUseCase:
        return SkipDayTextUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def confirm_reference(self) -> ConfirmReferenceUseCase:
        return ConfirmReferenceUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def _uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

"""Factories that bind application use cases to production adapters."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mood_tracker.application.use_cases import (
    AddFieldVersionUseCase,
    ConfirmReferenceUseCase,
    CreateFieldUseCase,
    CreateQuickEventUseCase,
    GetDayUseCase,
    GetEventsForDateUseCase,
    GetMonthCalendarUseCase,
    GetUserByTelegramIdUseCase,
    ListQuestionnaireFieldsUseCase,
    QuestionnaireFieldUseCase,
    RegisterUserUseCase,
    RenameFieldUseCase,
    SaveDayValueUseCase,
    SetFieldDisplayUseCase,
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

    def get_month_calendar(self) -> GetMonthCalendarUseCase:
        return GetMonthCalendarUseCase(self._uow())

    def get_events_for_date(self) -> GetEventsForDateUseCase:
        return GetEventsForDateUseCase(self._uow())

    def create_quick_event(self) -> CreateQuickEventUseCase:
        return CreateQuickEventUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def save_day_value(self) -> SaveDayValueUseCase:
        return SaveDayValueUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def skip_day_text(self) -> SkipDayTextUseCase:
        return SkipDayTextUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def confirm_reference(self) -> ConfirmReferenceUseCase:
        return ConfirmReferenceUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def list_questionnaire_fields(self) -> ListQuestionnaireFieldsUseCase:
        return ListQuestionnaireFieldsUseCase(self._uow())

    def questionnaire_field(self) -> QuestionnaireFieldUseCase:
        return QuestionnaireFieldUseCase(self._uow(), SystemClock())

    def create_field(self) -> CreateFieldUseCase:
        return CreateFieldUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def rename_field(self) -> RenameFieldUseCase:
        return RenameFieldUseCase(self._uow())

    def set_field_display(self) -> SetFieldDisplayUseCase:
        return SetFieldDisplayUseCase(self._uow())

    def add_field_version(self) -> AddFieldVersionUseCase:
        return AddFieldVersionUseCase(self._uow(), SystemClock(), Uuid7IdGenerator())

    def _uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

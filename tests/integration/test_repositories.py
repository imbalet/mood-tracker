import os
from datetime import UTC, datetime

import pytest

from mood_tracker.application.contracts.events import CreateEvent
from mood_tracker.application.contracts.users import RegisterUser
from mood_tracker.application.errors import IdentifierCollision
from mood_tracker.application.use_cases import CreateEventUseCase, RegisterUserUseCase
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.value_objects import UserTimezone
from mood_tracker.infrastructure.db.session import create_session_factory
from mood_tracker.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FixedClock:
    def now(self) -> datetime:
        return datetime(2025, 1, 2, tzinfo=UTC)


class Uuid7Generator:
    def new(self):
        from uuid import uuid7

        return uuid7()


async def test_register_persists_user_and_default_fields() -> None:
    engine, session_factory = create_session_factory(os.environ["TEST_DATABASE_URL"])
    try:
        use_case = RegisterUserUseCase(
            SqlAlchemyUnitOfWork(session_factory), FixedClock(), Uuid7Generator()
        )
        user = await use_case.execute(
            RegisterUser(123456, UserTimezone("Europe/Moscow"))
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            loaded = await uow.users.get(user.id)
            fields = await uow.fields.list_for_user(user.id)
            day_questionnaire = await uow.questionnaires.get(
                user.id, QuestionnaireKind.DAY
            )

        assert loaded == user
        assert len(fields) == 4
        assert day_questionnaire is not None
        assert any(
            placement.role is QuestionnaireFieldRole.DAY_STATE
            for placement in day_questionnaire.fields.values()
        )
    finally:
        await engine.dispose()


async def test_event_persists_without_questionnaire_snapshot() -> None:
    engine, session_factory = create_session_factory(os.environ["TEST_DATABASE_URL"])
    try:
        user = await RegisterUserUseCase(
            SqlAlchemyUnitOfWork(session_factory), FixedClock(), Uuid7Generator()
        ).execute(RegisterUser(234567, UserTimezone("Europe/Moscow")))
        event = await CreateEventUseCase(
            SqlAlchemyUnitOfWork(session_factory), Uuid7Generator()
        ).execute(
            CreateEvent(
                user.id,
                datetime(2025, 1, 2, 12, tzinfo=UTC),
                user.timezone,
            )
        )
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            loaded = await uow.events.get(user.id, event.id)

        assert loaded is not None
        assert loaded.occurred_timezone == user.timezone
        assert loaded.response.answers == {}
    finally:
        await engine.dispose()


async def test_questionnaire_rejects_duplicate_field_order() -> None:
    engine, session_factory = create_session_factory(os.environ["TEST_DATABASE_URL"])
    try:
        user = await RegisterUserUseCase(
            SqlAlchemyUnitOfWork(session_factory), FixedClock(), Uuid7Generator()
        ).execute(RegisterUser(345678, UserTimezone("Europe/Moscow")))

        with pytest.raises(IdentifierCollision):
            async with SqlAlchemyUnitOfWork(session_factory) as uow:
                questionnaire = await uow.questionnaires.get(
                    user.id, QuestionnaireKind.DAY
                )
                assert questionnaire is not None
                first, second, *_ = questionnaire.ordered_fields()
                second.sort_order = first.sort_order
                await uow.questionnaires.save(questionnaire)
                await uow.commit()
    finally:
        await engine.dispose()


async def test_questionnaire_persists_soft_deleted_placement() -> None:
    engine, session_factory = create_session_factory(os.environ["TEST_DATABASE_URL"])
    try:
        user = await RegisterUserUseCase(
            SqlAlchemyUnitOfWork(session_factory), FixedClock(), Uuid7Generator()
        ).execute(RegisterUser(456789, UserTimezone("Europe/Moscow")))
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            questionnaire = await uow.questionnaires.get(user.id, QuestionnaireKind.DAY)
            assert questionnaire is not None
            placement = next(
                item
                for item in questionnaire.fields.values()
                if item.role is QuestionnaireFieldRole.ORDINARY
            )
            questionnaire.delete(placement.field_id, FixedClock().now())
            await uow.questionnaires.save(questionnaire)
            await uow.commit()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            restored = await uow.questionnaires.get(user.id, QuestionnaireKind.DAY)

        assert restored is not None
        assert restored.fields[placement.field_id].deleted_at == FixedClock().now()
    finally:
        await engine.dispose()

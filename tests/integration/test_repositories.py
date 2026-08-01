from __future__ import annotations

import os
from datetime import UTC, datetime

from mood_tracker.application.commands import RegisterUser
from mood_tracker.application.use_cases import RegisterUserUseCase
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

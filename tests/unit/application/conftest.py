from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, create_autospec
from uuid import UUID, uuid7

import pytest

from mood_tracker.application.ports import (
    Clock,
    DayRepository,
    EventRepository,
    FieldRepository,
    IdGenerator,
    QuestionnaireRepository,
    ReferenceDaysRepository,
    UnitOfWork,
    UserRepository,
)
from mood_tracker.domain.entities import Questionnaire
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SequenceIdGenerator:
    def __init__(self, ids: list[UUID]) -> None:
        self._ids = deque(ids)

    def new(self) -> UUID:
        return self._ids.popleft()


@pytest.fixture
def clock(fixed_now: datetime) -> Clock:
    return FixedClock(fixed_now)


@pytest.fixture
def id_generator() -> IdGenerator:
    return SequenceIdGenerator([uuid7() for _ in range(64)])


@pytest.fixture
def uow() -> UnitOfWork:
    unit_of_work = create_autospec(UnitOfWork, instance=True)
    unit_of_work.__aenter__ = AsyncMock(return_value=unit_of_work)
    unit_of_work.__aexit__ = AsyncMock(return_value=False)
    unit_of_work.commit = AsyncMock()
    unit_of_work.rollback = AsyncMock()
    unit_of_work.users = create_autospec(UserRepository, instance=True)
    unit_of_work.fields = create_autospec(FieldRepository, instance=True)
    unit_of_work.questionnaires = create_autospec(
        QuestionnaireRepository, instance=True
    )

    async def questionnaire_for_user(
        user_id: UUID, kind: QuestionnaireKind
    ) -> Questionnaire:
        fields = await unit_of_work.fields.list_for_user(user_id)
        return Questionnaire(
            uuid7(),
            user_id,
            kind,
            {
                field.id: QuestionnaireField(
                    field.id,
                    index,
                    role=(
                        QuestionnaireFieldRole.EVENT_DESCRIPTION
                        if kind is QuestionnaireKind.EVENT and field.name == "Описание"
                        else (
                            QuestionnaireFieldRole.DAY_STATE
                            if (
                                kind is QuestionnaireKind.DAY
                                and field.name == "Состояние"
                            )
                            else QuestionnaireFieldRole.ORDINARY
                        )
                    ),
                )
                for index, field in enumerate(fields)
            },
        )

    unit_of_work.questionnaires.get = AsyncMock(side_effect=questionnaire_for_user)
    unit_of_work.days = create_autospec(DayRepository, instance=True)
    unit_of_work.events = create_autospec(EventRepository, instance=True)
    unit_of_work.reference_days = create_autospec(
        ReferenceDaysRepository, instance=True
    )
    return unit_of_work

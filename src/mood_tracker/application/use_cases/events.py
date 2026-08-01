"""Read and quick-capture event use cases."""

from collections.abc import Sequence

from mood_tracker.application.commands import CreateQuickEvent, GetEventsForDate
from mood_tracker.application.errors import UserNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._transactions import execute_write
from mood_tracker.domain.entities import Event, Field, Questionnaire
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.errors import InvalidFieldValue


def _description_field(
    fields: tuple[Field, ...], questionnaire: Questionnaire
) -> Field:
    field_ids = {
        placement.field_id
        for placement in questionnaire.fields.values()
        if placement.role is QuestionnaireFieldRole.EVENT_DESCRIPTION
    }
    field = next((candidate for candidate in fields if candidate.id in field_ids), None)
    if field is None:
        msg = "Event description field is unavailable"
        raise InvalidFieldValue(msg)
    return field


class GetEventsForDateUseCase:
    """Read events without creating a day draft."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetEventsForDate) -> Sequence[Event]:
        async with self._uow:
            return await self._uow.events.list_for_date(
                command.user_id, command.event_date
            )


class CreateQuickEventUseCase:
    """Persist a text-first event draft at the current instant."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: CreateQuickEvent) -> Event:
        async def operation() -> Event:
            user = await self._uow.users.get(command.user_id)
            if user is None:
                raise UserNotFound
            if not command.text.strip():
                msg = "Quick event text cannot be empty"
                raise InvalidFieldValue(msg)
            event = Event(
                id=self._id_generator.new(),
                user_id=user.id,
                occurred_at=self._clock.now(),
                occurred_timezone=user.timezone.name,
            )
            questionnaire = await self._uow.questionnaires.get(
                user.id, QuestionnaireKind.EVENT
            )
            if questionnaire is None:
                msg = "Event questionnaire is unavailable"
                raise InvalidFieldValue(msg)
            fields = tuple(await self._uow.fields.list_for_user(user.id))
            event.save_value(
                _description_field(fields, questionnaire).current_version, command.text
            )
            await self._uow.events.add(event)
            return event

        return await execute_write(self._uow, operation)

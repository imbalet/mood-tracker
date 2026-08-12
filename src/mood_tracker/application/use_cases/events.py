"""Read and quick-capture event use cases."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from mood_tracker.application.contracts.events import (
    ChangeEventTime,
    CompleteEvent,
    CreateEvent,
    CreateQuickEvent,
    DeleteEvent,
    GetEvent,
    GetEventsForDate,
    SaveEventValue,
    SkipEventField,
)
from mood_tracker.application.errors import EventNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    list_questionnaire_fields,
    require_enabled_questionnaire_field,
    require_questionnaire,
    require_user,
)
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import (
    Event,
    Field,
    Questionnaire,
)
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.errors import IncompleteDay, InvalidFieldValue


# TODO: здесь и везде продумать возможность не смешнивать сообщение исключений и логику
def _to_utc(value: datetime, label: str) -> datetime:
    """Normalize an aware application input to the domain's UTC invariant."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidFieldValue(f"{label} must include a timezone")
    return value.astimezone(UTC)


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
            user = await require_user(self._uow, command.user_id)
            # TODO: мб вынести подобные проверки на наличие текста в хенделеры \
            # в виде мидлваря или в ДТО как пост инит
            if not command.text.strip():
                msg = "Quick event text cannot be empty"
                raise InvalidFieldValue(msg)
            event = Event(
                id=self._id_generator.new(),
                user_id=user.id,
                occurred_at=self._clock.now(),
                occurred_timezone=user.timezone,
            )
            questionnaire = await self._uow.questionnaires.get(
                user.id, QuestionnaireKind.EVENT
            )
            if questionnaire is None:
                msg = "Event questionnaire is unavailable"
                raise InvalidFieldValue(msg)
            fields = tuple(
                item.field
                for item in await list_questionnaire_fields(
                    self._uow, user.id, questionnaire
                )
            )
            event.save_value(
                _description_field(fields, questionnaire).current_version, command.text
            )
            await self._uow.events.add(event)
            return event

        return await execute_write(self._uow, operation)


async def _require_event(uow: UnitOfWork, user_id: UUID, event_id: UUID) -> Event:
    event = await uow.events.get(user_id, event_id)
    if event is None:
        raise EventNotFound
    return event


class CreateEventUseCase:
    def __init__(self, uow: UnitOfWork, id_generator: IdGenerator) -> None:
        self._uow = uow
        self._id_generator = id_generator

    async def execute(self, command: CreateEvent) -> Event:
        async def operation() -> Event:
            await require_user(self._uow, command.user_id)
            event = Event(
                self._id_generator.new(),
                command.user_id,
                _to_utc(command.occurred_at, "Event occurrence time"),
                command.occurred_timezone,
            )
            await self._uow.events.add(event)
            return event

        return await execute_write(self._uow, operation)


class GetEventUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetEvent) -> Event:
        async with self._uow:
            event = await self._uow.events.get(command.user_id, command.event_id)
            if event is None:
                raise EventNotFound
            return event


class SaveEventValueUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SaveEventValue) -> Event:
        async def operation() -> Event:
            event = await _require_event(self._uow, command.user_id, command.event_id)
            _, field, _ = await require_enabled_questionnaire_field(
                self._uow,
                command.user_id,
                QuestionnaireKind.EVENT,
                command.field_id,
            )
            event.save_value(field.current_version, command.value)
            await self._uow.events.save(event)
            return event

        return await execute_transaction(self._uow, operation)


class SkipEventFieldUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SkipEventField) -> Event:
        async def operation() -> Event:
            event = await _require_event(self._uow, command.user_id, command.event_id)
            _, field, placement = await require_enabled_questionnaire_field(
                self._uow,
                command.user_id,
                QuestionnaireKind.EVENT,
                command.field_id,
            )
            if placement.is_required:
                raise InvalidFieldValue("Required event field cannot be skipped")
            event.skip_field(field.current_version)
            await self._uow.events.save(event)
            return event

        return await execute_transaction(self._uow, operation)


class CompleteEventUseCase:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, command: CompleteEvent) -> Event:
        async def operation() -> Event:
            event = await _require_event(self._uow, command.user_id, command.event_id)
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, QuestionnaireKind.EVENT
            )
            fields = {
                item.field.id: item.field
                for item in await list_questionnaire_fields(
                    self._uow, command.user_id, questionnaire
                )
            }
            required = [
                fields[field_id]
                for field_id, placement in questionnaire.fields.items()
                if placement.is_enabled and placement.is_required and field_id in fields
            ]
            if any(not event.has_completed_step(field.id) for field in required):
                raise IncompleteDay("Required event fields are unfinished")
            if not event.response.answers:
                event.delete(self._clock.now())
                await self._uow.events.save(event)
                return event
            event.complete(self._clock.now())
            await self._uow.events.save(event)
            return event

        return await execute_transaction(self._uow, operation)


class ChangeEventTimeUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ChangeEventTime) -> Event:
        async def operation() -> Event:
            event = await self._uow.events.get(command.user_id, command.event_id)
            if event is None:
                raise EventNotFound
            event.change_time(_to_utc(command.occurred_at, "Event occurrence time"))
            await self._uow.events.save(event)
            return event

        return await execute_transaction(self._uow, operation)


class DeleteEventUseCase:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, command: DeleteEvent) -> None:
        async def operation() -> None:
            event = await self._uow.events.get(command.user_id, command.event_id)
            if event is None:
                raise EventNotFound
            event.delete(self._clock.now())
            await self._uow.events.save(event)

        await execute_transaction(self._uow, operation)

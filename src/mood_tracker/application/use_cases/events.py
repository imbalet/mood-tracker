"""Read and quick-capture event use cases."""

from collections.abc import Sequence
from datetime import UTC, datetime

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
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    find_system_questionnaire_field,
    require_enabled_questionnaire_field,
    require_owned_event,
    require_questionnaire,
    require_user,
)
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import Event
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.errors import IncompleteDay, InvalidFieldValue


# TODO: здесь и везде продумать возможность не смешнивать сообщение исключений и логику
def _to_utc(value: datetime, label: str) -> datetime:
    """Normalize an aware application input to the domain's UTC invariant."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidFieldValue(f"{label} must include a timezone")
    return value.astimezone(UTC)


class GetEventsForDateUseCase:
    """Read events without creating a day draft."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetEventsForDate) -> Sequence[Event]:
        async with self._uow:
            await require_user(self._uow, command.user_id)
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
            description_field = await find_system_questionnaire_field(
                self._uow,
                user.id,
                questionnaire,
                QuestionnaireFieldRole.EVENT_DESCRIPTION,
            )
            if description_field is None:
                msg = "Event description field is unavailable"
                raise InvalidFieldValue(msg)
            event.save_value(description_field.current_version, command.text)
            await self._uow.events.add(event)
            return event

        return await execute_write(self._uow, operation)


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
            return await require_owned_event(
                self._uow, command.user_id, command.event_id
            )


class SaveEventValueUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SaveEventValue) -> Event:
        async def operation() -> Event:
            event = await require_owned_event(
                self._uow, command.user_id, command.event_id
            )
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
            event = await require_owned_event(
                self._uow, command.user_id, command.event_id
            )
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
            event = await require_owned_event(
                self._uow, command.user_id, command.event_id
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, QuestionnaireKind.EVENT
            )
            if any(
                not event.has_completed_step(field_id)
                for field_id in questionnaire.required_enabled_field_ids()
            ):
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
            event = await require_owned_event(
                self._uow, command.user_id, command.event_id
            )
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
            event = await require_owned_event(
                self._uow, command.user_id, command.event_id
            )
            event.delete(self._clock.now())
            await self._uow.events.save(event)

        await execute_transaction(self._uow, operation)

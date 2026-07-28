"""Day flow and reference-day use cases."""

from collections.abc import Sequence
from datetime import date
from functools import partial
from uuid import UUID
from zoneinfo import ZoneInfo

from mood_tracker.application.commands import (
    ConfirmReference,
    DayForm,
    GetDay,
    ReferenceReview,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.errors import DayNotFound, FieldNotFound, UserNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._transactions import execute_write
from mood_tracker.domain.entities import Day, Field, ReferenceDays, ScaleConfig
from mood_tracker.domain.entities.reference_days import boundary_reference_candidate
from mood_tracker.domain.enums import DayStatus, ReferenceType
from mood_tracker.domain.policies import CompletionPolicy


def _sorted_fields(fields: Sequence[Field]) -> tuple[Field, ...]:
    return tuple(sorted(fields, key=lambda field: field.sort_order))


def _next_field(day: Day | None, fields: Sequence[Field]) -> Field | None:
    if day is not None and day.status is DayStatus.COMPLETE:
        return None
    return next(
        (
            field
            for field in _sorted_fields(fields)
            if field.is_active and (day is None or not day.has_completed_step(field.id))
        ),
        None,
    )


def _reference_day_id(
    reference_days: ReferenceDays, type: ReferenceType
) -> UUID | None:
    return (
        reference_days.best_day_id
        if type is ReferenceType.BEST
        else reference_days.worst_day_id
    )


def _is_boundary_for(day: Day, core_field: Field, type: ReferenceType) -> bool:
    value = day.values.get(core_field.id)
    if value is None or not isinstance(value.value, int):
        return False
    version = core_field.get_version(value.field_version_id)
    if version is None or not isinstance(version.config, ScaleConfig):
        return False
    return (
        value.value == version.config.maximum
        if type is ReferenceType.BEST
        else value.value == version.config.minimum
    )


async def _valid_day_ids(
    uow: UnitOfWork,
    user_id: UUID,
    core_field: Field,
    reference_days: ReferenceDays,
    type: ReferenceType,
) -> set[UUID]:
    day_ids = tuple({reference.day_id for reference in reference_days.history})
    days = await uow.days.get_many(user_id, day_ids)
    return {day.id for day in days if _is_boundary_for(day, core_field, type)}


def _is_valid_reference_day(valid_ids: set[UUID], candidate: UUID) -> bool:
    return candidate in valid_ids


async def _load_day_for_edit(
    uow: UnitOfWork,
    id_generator: IdGenerator,
    user_id: UUID,
    day_date: date,
    field_id: UUID,
) -> tuple[Field, Day, bool]:
    """Load an owned field and date, creating an in-memory draft when absent."""
    user = await uow.users.get(user_id)
    if user is None:
        raise UserNotFound
    field = await uow.fields.get(user.id, field_id)
    if field is None:
        raise FieldNotFound
    day = await uow.days.get_by_date(user.id, day_date)
    if day is not None:
        return field, day, False
    return (
        field,
        Day(id=id_generator.new(), user_id=user.id, date=day_date),
        True,
    )


async def _rollback_if_invalid_current(
    uow: UnitOfWork,
    user_id: UUID,
    day: Day,
    core_field: Field,
    reference_days: ReferenceDays,
) -> bool:
    changed = False
    for type in ReferenceType:
        if _reference_day_id(reference_days, type) == day.id and not _is_boundary_for(
            day, core_field, type
        ):
            valid_ids = await _valid_day_ids(
                uow, user_id, core_field, reference_days, type
            )

            reference_days.rollback_current(
                type, partial(_is_valid_reference_day, valid_ids)
            )
            changed = True
    return changed


class GetDayUseCase:
    """Read a day and the next active questionnaire step without writing."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, command: GetDay) -> DayForm:
        """Return an existing day or an empty form for its user-local date."""
        async with self._uow:
            user = await self._uow.users.get(command.user_id)
            if user is None:
                raise UserNotFound
            day_date = (
                command.day_date
                or self._clock.now().astimezone(ZoneInfo(user.timezone.name)).date()
            )
            day = await self._uow.days.get_by_date(user.id, day_date)
            fields = _sorted_fields(await self._uow.fields.list_for_user(user.id))
            return DayForm(
                day_date=day_date,
                day=day,
                fields=fields,
                next_field=_next_field(day, fields),
            )


class SaveDayValueUseCase:
    """Save an answer, advance the draft and surface reference decisions."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: SaveDayValue) -> ReferenceReview | None:
        """Save the value and return a reference review only when it is needed."""

        async def operation() -> ReferenceReview | None:
            field, day, is_new = await _load_day_for_edit(
                self._uow,
                self._id_generator,
                command.user_id,
                command.day_date,
                command.field_id,
            )
            day.save_value(field.current_version, command.value)
            fields = await self._uow.fields.list_for_user(command.user_id)
            if day.status is DayStatus.DRAFT and all(
                not candidate.is_active or day.has_completed_step(candidate.id)
                for candidate in fields
            ):
                CompletionPolicy().complete(day, fields, self._clock.now())
            if is_new:
                await self._uow.days.add(day)
            else:
                await self._uow.days.save(day)
            if not field.is_core:
                return None
            return await self._handle_core_value(command.user_id, day, field)

        return await execute_write(self._uow, operation)

    async def _handle_core_value(
        self, user_id: UUID, day: Day, core_field: Field
    ) -> ReferenceReview | None:
        reference_days = await self._uow.reference_days.get(user_id)
        if reference_days is None:
            reference_days = ReferenceDays(user_id=user_id)
        if not reference_days.has_history:
            reference_days.initialize(
                day.id,
                self._id_generator.new(),
                self._id_generator.new(),
                self._clock.now(),
            )
            await self._uow.reference_days.save(reference_days)
            return None
        rolled_back = await _rollback_if_invalid_current(
            self._uow, user_id, day, core_field, reference_days
        )
        value = day.values[core_field.id].value
        if not isinstance(value, int) or not isinstance(
            core_field.current_version.config, ScaleConfig
        ):
            if rolled_back:
                await self._uow.reference_days.save(reference_days)
            return None
        type = boundary_reference_candidate(value, core_field.current_version.config)
        if type is None:
            if rolled_back:
                await self._uow.reference_days.save(reference_days)
            return None
        previous_reference_day_id = _reference_day_id(reference_days, type)
        if previous_reference_day_id is None:
            reference_days.establish_baseline(
                self._id_generator.new(), day.id, type, self._clock.now()
            )
            await self._uow.reference_days.save(reference_days)
            return None
        if rolled_back:
            await self._uow.reference_days.save(reference_days)
        if previous_reference_day_id == day.id:
            return None
        valid_boundary_ids = await _valid_day_ids(
            self._uow, user_id, core_field, reference_days, type
        )
        if not valid_boundary_ids:
            reference_days.apply_confirmed_change(
                self._id_generator.new(), day.id, type, self._clock.now()
            )
            await self._uow.reference_days.save(reference_days)
            return None
        return ReferenceReview(day.id, type, previous_reference_day_id)


class SkipDayTextUseCase:
    """Persist an explicit Text skip and advance the draft."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: SkipDayText) -> None:
        """Create or update a day after a deliberate Text skip."""

        async def operation() -> None:
            field, day, is_new = await _load_day_for_edit(
                self._uow,
                self._id_generator,
                command.user_id,
                command.day_date,
                command.field_id,
            )
            day.skip_text(field.current_version)
            fields = await self._uow.fields.list_for_user(command.user_id)
            if day.status is DayStatus.DRAFT and all(
                not candidate.is_active or day.has_completed_step(candidate.id)
                for candidate in fields
            ):
                CompletionPolicy().complete(day, fields, self._clock.now())
            if is_new:
                await self._uow.days.add(day)
            else:
                await self._uow.days.save(day)

        await execute_write(self._uow, operation)


class ConfirmReferenceUseCase:
    """Apply a user's answer to a requested boundary comparison."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: ConfirmReference) -> None:
        """Confirm a new record or roll back a rejected current reference."""

        async def operation() -> None:
            user = await self._uow.users.get(command.user_id)
            if user is None:
                raise UserNotFound
            day = await self._uow.days.get(user.id, command.day_id)
            if day is None:
                raise DayNotFound
            fields = await self._uow.fields.list_for_user(user.id)
            core_field = next((field for field in fields if field.is_core), None)
            if core_field is None:
                raise FieldNotFound
            reference_days = await self._uow.reference_days.get(user.id)
            if reference_days is None or not _is_boundary_for(
                day, core_field, command.type
            ):
                return
            current = _reference_day_id(reference_days, command.type)
            if command.is_new_record:
                if current is None:
                    reference_days.establish_baseline(
                        self._id_generator.new(),
                        day.id,
                        command.type,
                        self._clock.now(),
                    )
                elif current != day.id:
                    reference_days.apply_confirmed_change(
                        self._id_generator.new(),
                        day.id,
                        command.type,
                        self._clock.now(),
                    )
            elif current == day.id:
                valid_ids = await _valid_day_ids(
                    self._uow, user.id, core_field, reference_days, command.type
                )
                reference_days.rollback_current(
                    command.type, partial(_is_valid_reference_day, valid_ids)
                )
            await self._uow.reference_days.save(reference_days)

        await execute_write(self._uow, operation)

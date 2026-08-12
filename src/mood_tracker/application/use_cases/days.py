"""Day flow and reference-day use cases."""

from datetime import date
from functools import partial
from uuid import UUID

from mood_tracker.application.contracts.diary import (
    ConfirmReference,
    ReferenceReview,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.errors import DayNotFound, FieldNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    list_questionnaire_fields,
    require_enabled_questionnaire_field,
    require_questionnaire,
    require_user,
)
from mood_tracker.application.use_cases._transactions import execute_write
from mood_tracker.domain.entities import (
    Day,
    Field,
    ReferenceDays,
    ScaleConfig,
)
from mood_tracker.domain.entities.reference_days import boundary_reference_candidate
from mood_tracker.domain.enums import (
    DayStatus,
    QuestionnaireFieldRole,
    QuestionnaireKind,
    ReferenceType,
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
    value = day.response.answers.get(core_field.id)
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
    """Load an enabled day field and date, creating an in-memory draft when absent."""
    _, field, _ = await require_enabled_questionnaire_field(
        uow, user_id, QuestionnaireKind.DAY, field_id
    )
    day = await uow.days.get_by_date(user_id, day_date)
    if day is not None:
        return field, day, False
    return (
        field,
        Day(id=id_generator.new(), user_id=user_id, date=day_date),
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
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, QuestionnaireKind.DAY
            )
            fields = tuple(
                item.field
                for item in await list_questionnaire_fields(
                    self._uow, command.user_id, questionnaire
                )
            )
            active_field_ids = tuple(
                candidate.id
                for candidate in fields
                if questionnaire.fields[candidate.id].is_enabled
            )
            if day.status is DayStatus.DRAFT and all(
                day.has_completed_step(field_id) for field_id in active_field_ids
            ):
                day.complete(active_field_ids, self._clock.now())
            if is_new:
                await self._uow.days.add(day)
            else:
                await self._uow.days.save(day)
            placement = questionnaire.fields.get(field.id)
            if (
                placement is None
                or placement.role is not QuestionnaireFieldRole.DAY_STATE
            ):
                return None
            return await self._handle_core_value(command.user_id, day, field)

        return await execute_write(self._uow, operation)

    async def _handle_core_value(
        self, user_id: UUID, day: Day, core_field: Field
    ) -> ReferenceReview | None:
        # TODO: maybe extract to separate use case
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
        value = day.response.answers[core_field.id].value
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
            # TODO: unify with SaveDayValueUseCase
            field, day, is_new = await _load_day_for_edit(
                self._uow,
                self._id_generator,
                command.user_id,
                command.day_date,
                command.field_id,
            )
            day.skip_text(field.current_version)
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, QuestionnaireKind.DAY
            )
            fields = tuple(
                item.field
                for item in await list_questionnaire_fields(
                    self._uow, command.user_id, questionnaire
                )
            )
            active_field_ids = tuple(
                candidate.id
                for candidate in fields
                if questionnaire.fields[candidate.id].is_enabled
            )
            if day.status is DayStatus.DRAFT and all(
                day.has_completed_step(field_id) for field_id in active_field_ids
            ):
                day.complete(active_field_ids, self._clock.now())
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
            user = await require_user(self._uow, command.user_id)
            day = await self._uow.days.get(user.id, command.day_id)
            if day is None:
                raise DayNotFound
            questionnaire = await require_questionnaire(
                self._uow, user.id, QuestionnaireKind.DAY
            )
            fields = await self._uow.fields.list_for_user(user.id)
            core_field = next(
                (
                    field
                    for field in fields
                    if questionnaire.fields.get(field.id) is not None
                    and questionnaire.fields[field.id].role
                    is QuestionnaireFieldRole.DAY_STATE
                ),
                None,
            )
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

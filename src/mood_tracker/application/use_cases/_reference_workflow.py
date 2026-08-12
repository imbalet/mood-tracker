"""Reference-day decisions derived from saved daily state values."""

from uuid import UUID

from mood_tracker.application.contracts.diary import ReferenceReview
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.domain.entities import Day, Field, ReferenceDays, ScaleConfig
from mood_tracker.domain.entities.reference_days import boundary_reference_candidate
from mood_tracker.domain.enums import ReferenceType


def reference_day_id(reference_days: ReferenceDays, type: ReferenceType) -> UUID | None:
    """Return the current reference day for one direction."""
    return (
        reference_days.best_day_id
        if type is ReferenceType.BEST
        else reference_days.worst_day_id
    )


def is_boundary_for(day: Day, core_field: Field, type: ReferenceType) -> bool:
    """Whether a saved historical state value reaches one scale boundary."""
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


async def valid_day_ids(
    uow: UnitOfWork,
    user_id: UUID,
    core_field: Field,
    reference_days: ReferenceDays,
    type: ReferenceType,
) -> set[UUID]:
    """Return historical reference days that still match their stored boundary."""
    day_ids = tuple({reference.day_id for reference in reference_days.history})
    days = await uow.days.get_many(user_id, day_ids)
    return {day.id for day in days if is_boundary_for(day, core_field, type)}


async def rollback_invalid_current_references(
    uow: UnitOfWork,
    user_id: UUID,
    day: Day,
    core_field: Field,
    reference_days: ReferenceDays,
) -> bool:
    """Roll back current pointers when the edited day no longer reaches a boundary."""
    changed = False
    for type in ReferenceType:
        if reference_day_id(reference_days, type) == day.id and not is_boundary_for(
            day, core_field, type
        ):
            valid_ids = await valid_day_ids(
                uow, user_id, core_field, reference_days, type
            )
            reference_days.rollback_current(type, valid_ids.__contains__)
            changed = True
    return changed


async def review_state_change(
    uow: UnitOfWork,
    clock: Clock,
    id_generator: IdGenerator,
    user_id: UUID,
    day: Day,
    core_field: Field,
) -> ReferenceReview | None:
    """Persist automatic reference changes or request a user confirmation."""
    # TODO: maybe refactor
    reference_days = await uow.reference_days.get(user_id)
    if reference_days is None:
        reference_days = ReferenceDays(user_id=user_id)
    if not reference_days.has_history:
        reference_days.initialize(
            day.id,
            id_generator.new(),
            id_generator.new(),
            clock.now(),
        )
        await uow.reference_days.save(reference_days)
        return None

    rolled_back = await rollback_invalid_current_references(
        uow, user_id, day, core_field, reference_days
    )
    value = day.response.answers[core_field.id].value
    if not isinstance(value, int) or not isinstance(
        core_field.current_version.config, ScaleConfig
    ):
        if rolled_back:
            await uow.reference_days.save(reference_days)
        return None
    type = boundary_reference_candidate(value, core_field.current_version.config)
    if type is None:
        if rolled_back:
            await uow.reference_days.save(reference_days)
        return None
    previous_reference_day_id = reference_day_id(reference_days, type)
    if previous_reference_day_id is None:
        reference_days.establish_baseline(id_generator.new(), day.id, type, clock.now())
        await uow.reference_days.save(reference_days)
        return None
    if rolled_back:
        await uow.reference_days.save(reference_days)
    if previous_reference_day_id == day.id:
        return None
    valid_boundary_ids = await valid_day_ids(
        uow, user_id, core_field, reference_days, type
    )
    if not valid_boundary_ids:
        reference_days.apply_confirmed_change(
            id_generator.new(), day.id, type, clock.now()
        )
        await uow.reference_days.save(reference_days)
        return None
    return ReferenceReview(day.id, type, previous_reference_day_id)


async def confirm_reference_change(
    uow: UnitOfWork,
    clock: Clock,
    id_generator: IdGenerator,
    user_id: UUID,
    day: Day,
    core_field: Field,
    type: ReferenceType,
    is_new_record: bool,
) -> None:
    """Apply a user's confirmation or rejection of a reference change."""
    reference_days = await uow.reference_days.get(user_id)
    if reference_days is None or not is_boundary_for(day, core_field, type):
        return
    current = reference_day_id(reference_days, type)
    if is_new_record:
        if current is None:
            reference_days.establish_baseline(
                id_generator.new(), day.id, type, clock.now()
            )
        elif current != day.id:
            reference_days.apply_confirmed_change(
                id_generator.new(), day.id, type, clock.now()
            )
    elif current == day.id:
        valid_ids = await valid_day_ids(uow, user_id, core_field, reference_days, type)
        reference_days.rollback_current(type, valid_ids.__contains__)
    await uow.reference_days.save(reference_days)

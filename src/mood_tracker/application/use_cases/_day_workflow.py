"""Shared write workflow for editable diary days."""

from datetime import date
from uuid import UUID

from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    require_enabled_questionnaire_field,
    require_questionnaire,
)
from mood_tracker.domain.entities import Day, Field
from mood_tracker.domain.enums import DayStatus, QuestionnaireKind


async def load_day_for_edit(
    uow: UnitOfWork,
    id_generator: IdGenerator,
    user_id: UUID,
    day_date: date,
    field_id: UUID,
) -> tuple[Field, Day, bool]:
    """Load an enabled day field and its day, creating a draft when absent."""
    _, field, _ = await require_enabled_questionnaire_field(
        uow, user_id, QuestionnaireKind.DAY, field_id
    )
    day = await uow.days.get_by_date(user_id, day_date)
    if day is not None:
        return field, day, False
    return field, Day(id_generator.new(), user_id, day_date), True


async def complete_and_persist_day(
    uow: UnitOfWork,
    clock: Clock,
    user_id: UUID,
    day: Day,
    is_new: bool,
) -> None:
    """Complete an eligible draft and persist it as new or existing data."""
    questionnaire = await require_questionnaire(uow, user_id, QuestionnaireKind.DAY)
    active_field_ids = questionnaire.enabled_field_ids()
    if day.status is DayStatus.DRAFT and all(
        day.has_completed_step(field_id) for field_id in active_field_ids
    ):
        day.complete(active_field_ids, clock.now())
    if is_new:
        await uow.days.add(day)
    else:
        await uow.days.save(day)

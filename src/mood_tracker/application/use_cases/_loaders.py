"""Shared owner-scoped aggregate loading for application use cases."""

from uuid import UUID

from mood_tracker.application.contracts.questionnaires import QuestionnaireFieldItem
from mood_tracker.application.errors import (
    DayNotFound,
    EventNotFound,
    FieldNotFound,
    UserNotFound,
)
from mood_tracker.application.ports import UnitOfWork
from mood_tracker.domain.entities import Day, Event, Field, Questionnaire, UserProfile
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind


async def require_user(uow: UnitOfWork, user_id: UUID) -> UserProfile:
    """Return an accessible user profile or raise the application-level error."""
    user = await uow.users.get(user_id)
    if user is None:
        raise UserNotFound
    return user


async def require_owned_field(uow: UnitOfWork, user_id: UUID, field_id: UUID) -> Field:
    """Return a field only when it belongs to the requested user."""
    field = await uow.fields.get(user_id, field_id)
    if field is None:
        raise FieldNotFound
    return field


async def require_owned_day(uow: UnitOfWork, user_id: UUID, day_id: UUID) -> Day:
    """Return a day only when it belongs to an accessible user."""
    await require_user(uow, user_id)
    day = await uow.days.get(user_id, day_id)
    if day is None:
        raise DayNotFound
    return day


async def require_owned_event(uow: UnitOfWork, user_id: UUID, event_id: UUID) -> Event:
    """Return an event only when it belongs to an accessible user."""
    await require_user(uow, user_id)
    event = await uow.events.get(user_id, event_id)
    if event is None:
        raise EventNotFound
    return event


async def require_questionnaire(
    uow: UnitOfWork, user_id: UUID, kind: QuestionnaireKind
) -> Questionnaire:
    """Return one owner-scoped questionnaire or conceal its absence as a field error."""
    questionnaire = await uow.questionnaires.get(user_id, kind)
    if questionnaire is None:
        raise FieldNotFound
    return questionnaire


async def list_questionnaire_fields(
    uow: UnitOfWork, user_id: UUID, questionnaire: Questionnaire
) -> tuple[QuestionnaireFieldItem, ...]:
    """Resolve existing user fields in the questionnaire's placement order."""
    fields = {field.id: field for field in await uow.fields.list_for_user(user_id)}
    return tuple(
        QuestionnaireFieldItem(fields[placement.field_id], placement)
        for placement in questionnaire.ordered_fields()
        if placement.field_id in fields
    )


async def find_system_questionnaire_field(
    uow: UnitOfWork,
    user_id: UUID,
    questionnaire: Questionnaire,
    role: QuestionnaireFieldRole,
) -> Field | None:
    """Return an existing field assigned to a questionnaire system role."""
    fields = {field.id: field for field in await uow.fields.list_for_user(user_id)}
    return next(
        (
            fields[placement.field_id]
            for placement in questionnaire.ordered_fields()
            if placement.role is role and placement.field_id in fields
        ),
        None,
    )


async def require_enabled_questionnaire_field(
    uow: UnitOfWork,
    user_id: UUID,
    kind: QuestionnaireKind,
    field_id: UUID,
) -> tuple[Questionnaire, Field, QuestionnaireField]:
    """Load a visible field attached to one of a user's questionnaires."""
    await require_user(uow, user_id)
    questionnaire = await require_questionnaire(uow, user_id, kind)
    field = await require_owned_field(uow, user_id, field_id)
    placement = questionnaire.fields.get(field.id)
    if placement is None or not placement.is_enabled:
        raise FieldNotFound
    return questionnaire, field, placement

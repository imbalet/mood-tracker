"""Read models for current and historical reference-day views."""

from mood_tracker.application.contracts.diary import ConfirmReference
from mood_tracker.application.contracts.references import (
    GetReferenceHistory,
    ReferenceHistory,
)
from mood_tracker.application.errors import DayNotFound, FieldNotFound, UserNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    list_questionnaire_fields,
    require_questionnaire,
    require_user,
)
from mood_tracker.application.use_cases._reference_workflow import (
    confirm_reference_change,
)
from mood_tracker.application.use_cases._transactions import execute_write
from mood_tracker.domain.enums import (
    QuestionnaireFieldRole,
    QuestionnaireKind,
    ReferenceType,
)


class GetReferenceHistoryUseCase:
    """Expose active chains separately from the immutable audit journal."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetReferenceHistory) -> ReferenceHistory:
        """Return an empty history for a user without any state values yet."""
        async with self._uow:
            if await self._uow.users.get(command.user_id) is None:
                raise UserNotFound
            reference_days = await self._uow.reference_days.get(command.user_id)
            if reference_days is None:
                return ReferenceHistory((), (), ())
            return ReferenceHistory(
                best_chain=reference_days.active_chain(ReferenceType.BEST),
                worst_chain=reference_days.active_chain(ReferenceType.WORST),
                all_events=tuple(reference_days.history),
            )


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
            items = await list_questionnaire_fields(self._uow, user.id, questionnaire)
            core_field = next(
                (
                    item.field
                    for item in items
                    if item.placement.role is QuestionnaireFieldRole.DAY_STATE
                ),
                None,
            )
            if core_field is None:
                raise FieldNotFound
            await confirm_reference_change(
                self._uow,
                self._clock,
                self._id_generator,
                user.id,
                day,
                core_field,
                command.type,
                command.is_new_record,
            )

        await execute_write(self._uow, operation)

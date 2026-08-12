"""Write use cases for values and explicit skips in a diary day."""

from mood_tracker.application.contracts.diary import (
    ReferenceReview,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._day_workflow import (
    complete_and_persist_day,
    load_day_for_edit,
)
from mood_tracker.application.use_cases._loaders import require_questionnaire
from mood_tracker.application.use_cases._reference_workflow import review_state_change
from mood_tracker.application.use_cases._transactions import execute_write
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind


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
            field, day, is_new = await load_day_for_edit(
                self._uow,
                self._id_generator,
                command.user_id,
                command.day_date,
                command.field_id,
            )
            day.save_value(field.current_version, command.value)
            await complete_and_persist_day(
                self._uow, self._clock, command.user_id, day, is_new
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, QuestionnaireKind.DAY
            )
            placement = questionnaire.fields.get(field.id)
            if (
                placement is None
                or placement.role is not QuestionnaireFieldRole.DAY_STATE
            ):
                return None
            return await review_state_change(
                self._uow,
                self._clock,
                self._id_generator,
                command.user_id,
                day,
                field,
            )

        return await execute_write(self._uow, operation)


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
            field, day, is_new = await load_day_for_edit(
                self._uow,
                self._id_generator,
                command.user_id,
                command.day_date,
                command.field_id,
            )
            day.skip_text(field.current_version)
            await complete_and_persist_day(
                self._uow, self._clock, command.user_id, day, is_new
            )

        await execute_write(self._uow, operation)

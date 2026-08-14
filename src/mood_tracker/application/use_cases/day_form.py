"""Read and navigate one user's day questionnaire."""

from mood_tracker.application.contracts.diary import DayForm, GetDay
from mood_tracker.application.contracts.questionnaires import QuestionnaireFieldItem
from mood_tracker.application.ports import Clock, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    list_questionnaire_fields,
    require_questionnaire,
    require_user,
)
from mood_tracker.domain.entities import Day, Field
from mood_tracker.domain.enums import DayStatus, QuestionnaireKind


def next_unfinished_field(
    day: Day | None, items: tuple[QuestionnaireFieldItem, ...]
) -> Field | None:
    """Return the next enabled placement that has no saved progress."""
    if day is not None and day.status is DayStatus.COMPLETE:
        return None
    return next(
        (
            item.field
            for item in items
            if (
                item.placement.is_enabled
                and (day is None or not day.has_completed_step(item.field.id))
            )
        ),
        None,
    )


class GetDayUseCase:
    """Read a day and the next active questionnaire step without writing."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, command: GetDay) -> DayForm:
        """Return an existing day or an empty form for its user-local date."""
        async with self._uow:
            user = await require_user(self._uow, command.user_id)
            day_date = command.day_date or user.timezone.local_date_at(
                self._clock.now()
            )
            day = await self._uow.days.get_by_date(user.id, day_date)
            questionnaire = await require_questionnaire(
                self._uow, user.id, QuestionnaireKind.DAY
            )
            items = await list_questionnaire_fields(self._uow, user.id, questionnaire)
            fields = tuple(item.field for item in items)
            return DayForm(
                day_date=day_date,
                day=day,
                fields=fields,
                placements=questionnaire.fields,
                next_field=next_unfinished_field(day, items),
            )

"""Read a user's diary data for one calendar month."""

from mood_tracker.application.contracts.calendar import GetMonthCalendar, MonthCalendar
from mood_tracker.application.errors import UserNotFound
from mood_tracker.application.ports import UnitOfWork
from mood_tracker.domain.enums import QuestionnaireKind


class GetMonthCalendarUseCase:
    """Return only the selected owner's data for a calendar month."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetMonthCalendar) -> MonthCalendar:
        """Load days and current field display settings for a month."""
        month = command.month.replace(day=1)
        async with self._uow:
            user = await self._uow.users.get(command.user_id)
            if user is None:
                raise UserNotFound
            days = await self._uow.days.list_for_month(user.id, month)
            fields = await self._uow.fields.list_for_user(user.id)
            questionnaire = await self._uow.questionnaires.get(
                user.id, QuestionnaireKind.DAY
            )
            references = await self._uow.reference_days.get(user.id)
            return MonthCalendar(
                month=month,
                days=tuple(days),
                fields=tuple(fields),
                references=references,
                placements=({} if questionnaire is None else questionnaire.fields),
            )

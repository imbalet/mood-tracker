"""Builder for user-day aggregates."""

from datetime import date, datetime
from uuid import UUID, uuid7

from mood_tracker.domain.entities import Day, QuestionnaireResponse
from mood_tracker.domain.enums import DayStatus


class DayFactory:
    """Build day aggregates with independent mutable collections."""

    def build(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        day_date: date = date(2025, 1, 2),
        status: DayStatus = DayStatus.DRAFT,
        completed_at: datetime | None = None,
        response: QuestionnaireResponse | None = None,
    ) -> Day:
        """Build a day with copied values and questionnaire progress."""
        return Day(
            id=id or uuid7(),
            user_id=user_id or uuid7(),
            date=day_date,
            status=status,
            completed_at=completed_at,
            response=response or QuestionnaireResponse(),
        )

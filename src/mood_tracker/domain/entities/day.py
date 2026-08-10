"""Day aggregate, field-step progress and versioned values."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.entities.questionnaire import Answer, QuestionnaireResponse
from mood_tracker.domain.enums import DayStatus, FieldType
from mood_tracker.domain.errors import IncompleteDay, InvalidFieldValue
from mood_tracker.domain.value_objects import require_utc


@dataclass(slots=True)
class Day:
    """One editable user day that preserves values and questionnaire progress."""

    id: UUID
    user_id: UUID
    date: date
    status: DayStatus = DayStatus.DRAFT
    completed_at: datetime | None = None
    response: QuestionnaireResponse = field(default_factory=QuestionnaireResponse)

    def __post_init__(self) -> None:
        if self.completed_at is not None:
            self.completed_at = require_utc(self.completed_at, "Day completion time")

    def save_value(self, field_version: FieldVersion, value: int | str) -> Answer:
        return self.response.answer(field_version=field_version, value=value)

    def skip_text(self, field_version: FieldVersion) -> None:
        """Record a deliberate text-field skip without creating an Answer."""
        if field_version.type is not FieldType.TEXT:
            msg = "Only text fields may be skipped"
            raise InvalidFieldValue(msg)
        self.response.skip(field_version=field_version)

    def has_completed_step(self, field_id: UUID) -> bool:
        return self.response.has_completed_step(field_id=field_id)

    def complete(self, field_ids: Iterable[UUID], completed_at: datetime) -> None:
        """Complete a day only when every supplied active field has progress."""
        missing_ids = [
            field_id for field_id in field_ids if not self.has_completed_step(field_id)
        ]
        if missing_ids:
            msg = f"Day has {len(missing_ids)} unfinished active field(s)"
            raise IncompleteDay(msg)

        self.status = DayStatus.COMPLETE
        self.completed_at = require_utc(completed_at, "Day completion time")

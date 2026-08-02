"""Day aggregate, field-step progress and versioned values."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.enums import DayStatus, FieldType
from mood_tracker.domain.errors import IncompleteDay, InvalidFieldValue


@dataclass(frozen=True, slots=True)
class DayValue:
    """A concrete value saved with the semantic field version that defined it."""

    day_id: UUID
    field_id: UUID
    field_version_id: UUID
    value: int | str
    normalized_value: float | None

    @classmethod
    def from_input(
        cls, day_id: UUID, field_version: FieldVersion, value: int | str
    ) -> DayValue:
        """Validate user input against a version and construct a stored value."""
        normalized_value = field_version.validate_value(value)
        return cls(
            day_id=day_id,
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            value=value,
            normalized_value=normalized_value,
        )


@dataclass(frozen=True, slots=True)
class DayFieldProgress:
    """A persisted fact that the user answered or skipped one field step."""

    field_id: UUID
    field_version_id: UUID
    skipped: bool


@dataclass(slots=True)
class Day:
    """One editable user day that preserves values and questionnaire progress."""

    id: UUID
    user_id: UUID
    date: date
    status: DayStatus = DayStatus.DRAFT
    completed_at: datetime | None = None
    values: dict[UUID, DayValue] = field(default_factory=dict)
    progress: dict[UUID, DayFieldProgress] = field(default_factory=dict)

    def save_value(self, field_version: FieldVersion, value: int | str) -> DayValue:
        """Save or replace a value and mark its field step as completed."""
        day_value = DayValue.from_input(self.id, field_version, value)
        self.values[field_version.field_id] = day_value
        self.progress[field_version.field_id] = DayFieldProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=False,
        )
        return day_value

    def skip_text(self, field_version: FieldVersion) -> None:
        """Record a deliberate text-field skip without creating a DayValue."""
        if field_version.type is not FieldType.TEXT:
            msg = "Only text fields may be skipped"
            raise InvalidFieldValue(msg)
        self.values.pop(field_version.field_id, None)
        self.progress[field_version.field_id] = DayFieldProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=True,
        )

    def has_completed_step(self, field_id: UUID) -> bool:
        """Whether the questionnaire step has been answered or explicitly skipped."""
        return field_id in self.progress

    def complete(self, field_ids: Iterable[UUID], completed_at: datetime) -> None:
        """Complete a day only when every supplied active field has progress."""
        missing_ids = [
            field_id for field_id in field_ids if not self.has_completed_step(field_id)
        ]
        if missing_ids:
            msg = f"Day has {len(missing_ids)} unfinished active field(s)"
            raise IncompleteDay(msg)

        self.status = DayStatus.COMPLETE
        self.completed_at = completed_at

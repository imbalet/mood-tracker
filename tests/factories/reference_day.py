"""Builder for personal best/worst reference-day history entries."""

from datetime import UTC, datetime
from uuid import UUID, uuid7

from mood_tracker.domain.entities import ReferenceDay
from mood_tracker.domain.enums import ReferenceType


class ReferenceDayFactory:
    """Build reference-day entries with valid UUIDv7 defaults."""

    def build(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        day_id: UUID | None = None,
        type: ReferenceType = ReferenceType.WORST,
        previous_reference_day_id: UUID | None = None,
        created_at: datetime = datetime(2025, 1, 2, tzinfo=UTC),
    ) -> ReferenceDay:
        """Build a valid reference-day history entry."""
        return ReferenceDay(
            id=id or uuid7(),
            user_id=user_id or uuid7(),
            day_id=day_id or uuid7(),
            type=type,
            previous_reference_day_id=previous_reference_day_id,
            created_at=created_at,
        )

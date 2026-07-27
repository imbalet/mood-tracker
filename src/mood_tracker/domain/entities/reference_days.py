"""Personal best/worst reference days and their change history."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.field import ScaleConfig
from mood_tracker.domain.enums import ReferenceType
from mood_tracker.domain.errors import ReferenceDayViolation


@dataclass(frozen=True, slots=True)
class ReferenceDay:
    """An immutable fact that a day became the current personal reference."""

    id: UUID
    user_id: UUID
    day_id: UUID
    type: ReferenceType
    previous_reference_day_id: UUID | None
    created_at: datetime


@dataclass(slots=True)
class ReferenceDays:
    """Current best/worst reference days and their append-only history."""

    user_id: UUID
    best_day_id: UUID | None = None
    worst_day_id: UUID | None = None
    history: list[ReferenceDay] = field(default_factory=list)

    @property
    def is_initialized(self) -> bool:
        """Whether the first state value established both reference points."""
        return self.best_day_id is not None and self.worst_day_id is not None

    def initialize(
        self,
        day_id: UUID,
        best_reference_id: UUID,
        worst_reference_id: UUID,
        created_at: datetime,
    ) -> tuple[ReferenceDay, ReferenceDay]:
        """Make the first recorded state day both the best and worst reference."""
        if self.is_initialized:
            msg = "Reference days are already initialized"
            raise ReferenceDayViolation(msg)
        self.best_day_id = day_id
        self.worst_day_id = day_id
        best_reference = ReferenceDay(
            id=best_reference_id,
            user_id=self.user_id,
            day_id=day_id,
            type=ReferenceType.BEST,
            previous_reference_day_id=None,
            created_at=created_at,
        )
        worst_reference = ReferenceDay(
            id=worst_reference_id,
            user_id=self.user_id,
            day_id=day_id,
            type=ReferenceType.WORST,
            previous_reference_day_id=None,
            created_at=created_at,
        )
        self.history.extend((best_reference, worst_reference))
        return best_reference, worst_reference

    def apply_confirmed_change(
        self,
        reference_id: UUID,
        day_id: UUID,
        type: ReferenceType,
        created_at: datetime,
    ) -> ReferenceDay:
        """Apply a user-confirmed new best or worst reference day."""
        if not self.is_initialized:
            msg = "Reference days must be initialized before changing a reference"
            raise ReferenceDayViolation(msg)
        previous_reference_day_id = (
            self.best_day_id if type is ReferenceType.BEST else self.worst_day_id
        )
        reference = ReferenceDay(
            id=reference_id,
            user_id=self.user_id,
            day_id=day_id,
            type=type,
            previous_reference_day_id=previous_reference_day_id,
            created_at=created_at,
        )
        if type is ReferenceType.BEST:
            self.best_day_id = day_id
        else:
            self.worst_day_id = day_id
        self.history.append(reference)
        return reference


def boundary_reference_candidate(
    value: int, config: ScaleConfig
) -> ReferenceType | None:
    """Return a reference type only when state reaches a scale boundary."""
    config.normalize(value)
    if value == config.minimum:
        return ReferenceType.WORST
    if value == config.maximum:
        return ReferenceType.BEST
    return None

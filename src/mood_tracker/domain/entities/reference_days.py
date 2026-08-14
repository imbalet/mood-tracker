"""Personal best/worst reference days and their change history."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.day import Day
from mood_tracker.domain.entities.field import Field, ScaleConfig
from mood_tracker.domain.enums import ReferenceType
from mood_tracker.domain.errors import ReferenceDayViolation
from mood_tracker.domain.value_objects import require_utc


@dataclass(frozen=True, slots=True)
class ReferenceDay:
    """An immutable fact that a day became the current personal reference."""

    id: UUID
    user_id: UUID
    day_id: UUID
    type: ReferenceType
    previous_reference_day_id: UUID | None
    created_at: datetime

    def __post_init__(self) -> None:
        require_utc(self.created_at, "Reference creation time")


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

    @property
    def has_history(self) -> bool:
        """Whether the user has ever had a confirmed reference point."""
        return bool(self.history)

    def current_day_id(self, reference_type: ReferenceType) -> UUID | None:
        """Return the current reference day for one direction."""
        return (
            self.best_day_id
            if reference_type is ReferenceType.BEST
            else self.worst_day_id
        )

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
        created_at = require_utc(created_at, "Reference creation time")
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
        created_at = require_utc(created_at, "Reference creation time")
        previous_reference_day_id = self.current_day_id(type)
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

    def establish_baseline(
        self,
        reference_id: UUID,
        day_id: UUID,
        type: ReferenceType,
        created_at: datetime,
    ) -> ReferenceDay:
        """Set a missing directional reference without affecting the other one."""
        created_at = require_utc(created_at, "Reference creation time")
        previous_reference_day_id = self.current_day_id(type)
        if previous_reference_day_id is not None:
            msg = "A baseline can only be established for a missing direction"
            raise ReferenceDayViolation(msg)
        reference = ReferenceDay(
            id=reference_id,
            user_id=self.user_id,
            day_id=day_id,
            type=type,
            previous_reference_day_id=None,
            created_at=created_at,
        )
        if type is ReferenceType.BEST:
            self.best_day_id = day_id
        else:
            self.worst_day_id = day_id
        self.history.append(reference)
        return reference

    def rollback_current(
        self, type: ReferenceType, is_valid: Callable[[UUID], bool]
    ) -> UUID | None:
        """Move a current pointer back to the nearest valid prior reference."""
        current_day_id = self.current_day_id(type)
        candidate_day_id = self._previous_day_id(current_day_id, type)
        while candidate_day_id is not None:
            if is_valid(candidate_day_id):
                if type is ReferenceType.BEST:
                    self.best_day_id = candidate_day_id
                else:
                    self.worst_day_id = candidate_day_id
                return candidate_day_id
            candidate_day_id = self._previous_day_id(candidate_day_id, type)
        if type is ReferenceType.BEST:
            self.best_day_id = None
        else:
            self.worst_day_id = None
        return None

    def active_chain(self, reference_type: ReferenceType) -> tuple[ReferenceDay, ...]:
        """Return the current non-retracted history chain for one direction."""
        current_day_id = self.current_day_id(reference_type)
        chain: list[ReferenceDay] = []
        while current_day_id is not None:
            reference = next(
                (
                    event
                    for event in reversed(self.history)
                    if event.type is reference_type and event.day_id == current_day_id
                ),
                None,
            )
            if reference is None:
                break
            chain.append(reference)
            current_day_id = reference.previous_reference_day_id
        return tuple(reversed(chain))

    def _previous_day_id(self, day_id: UUID | None, type: ReferenceType) -> UUID | None:
        if day_id is None:
            return None
        for reference in reversed(self.history):
            if reference.type is type and reference.day_id == day_id:
                return reference.previous_reference_day_id
        return None


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


def is_reference_boundary(
    day: Day, core_field: Field, reference_type: ReferenceType
) -> bool:
    """Whether a saved core-field answer reaches one reference boundary."""
    value = day.response.answers.get(core_field.id)
    if value is None or not isinstance(value.value, int):
        return False
    version = core_field.get_version(value.field_version_id)
    if version is None or not isinstance(version.config, ScaleConfig):
        return False
    return (
        value.value == version.config.maximum
        if reference_type is ReferenceType.BEST
        else value.value == version.config.minimum
    )

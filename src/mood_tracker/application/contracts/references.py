"""Reference-history application contracts."""

from dataclasses import dataclass, field
from uuid import UUID

from mood_tracker.domain.entities import ReferenceDay


@dataclass(frozen=True, slots=True)
class GetReferenceHistory:
    """Read current reference chains and the immutable full event journal."""

    user_id: UUID


@dataclass(frozen=True, slots=True)
class ReferenceHistory:
    """Current best/worst chains alongside every confirmed historical event."""

    best_chain: tuple[ReferenceDay, ...] = field(default_factory=tuple)
    worst_chain: tuple[ReferenceDay, ...] = field(default_factory=tuple)
    all_events: tuple[ReferenceDay, ...] = field(default_factory=tuple)

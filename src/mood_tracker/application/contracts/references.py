"""Reference-history application contracts."""

from dataclasses import dataclass
from uuid import UUID

from mood_tracker.domain.entities import ReferenceDay


@dataclass(frozen=True, slots=True)
class GetReferenceHistory:
    """Read current reference chains and the immutable full event journal."""

    user_id: UUID


@dataclass(frozen=True, slots=True)
class ReferenceHistory:
    """Current best/worst chains alongside every confirmed historical event."""

    best_chain: tuple[ReferenceDay, ...]
    worst_chain: tuple[ReferenceDay, ...]
    all_events: tuple[ReferenceDay, ...]

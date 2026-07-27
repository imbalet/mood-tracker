from datetime import UTC, datetime
from uuid import uuid7

from mood_tracker.domain.entities.field import ScaleConfig
from mood_tracker.domain.entities.reference_days import (
    ReferenceDays,
    boundary_reference_candidate,
)
from mood_tracker.domain.enums import ReferenceType


def test_first_state_day_initializes_both_reference_directions() -> None:
    reference_days = ReferenceDays(user_id=uuid7())
    day_id = uuid7()

    references = reference_days.initialize(day_id, uuid7(), uuid7(), datetime.now(UTC))

    assert reference_days.best_day_id == day_id
    assert reference_days.worst_day_id == day_id
    assert {reference.type for reference in references} == {
        ReferenceType.BEST,
        ReferenceType.WORST,
    }


def test_boundary_reference_candidate_only_exists_at_scale_edges() -> None:
    config = ScaleConfig(0, 10)

    assert boundary_reference_candidate(0, config) is ReferenceType.WORST
    assert boundary_reference_candidate(10, config) is ReferenceType.BEST
    assert boundary_reference_candidate(5, config) is None

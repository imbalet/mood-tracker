from datetime import UTC, datetime
from uuid import uuid7

from mood_tracker.domain.entities.field import ScaleConfig
from mood_tracker.domain.entities.reference_days import (
    ReferenceDays,
    boundary_reference_candidate,
)
from mood_tracker.domain.enums import ReferenceType
from tests.factories import FieldFactory


def test_first_state_day_initializes_both_reference_directions(
    fixed_now: datetime,
) -> None:
    reference_days = ReferenceDays(user_id=uuid7())
    day_id = uuid7()

    references = reference_days.initialize(day_id, uuid7(), uuid7(), fixed_now)

    assert reference_days.best_day_id == day_id
    assert reference_days.worst_day_id == day_id
    assert {reference.type for reference in references} == {
        ReferenceType.BEST,
        ReferenceType.WORST,
    }


def test_boundary_reference_candidate_only_exists_at_scale_edges(
    field_factory: FieldFactory,
) -> None:
    config = field_factory.scale().current_version.config

    assert isinstance(config, ScaleConfig)
    assert boundary_reference_candidate(0, config) is ReferenceType.WORST
    assert boundary_reference_candidate(10, config) is ReferenceType.BEST
    assert boundary_reference_candidate(5, config) is None


def test_rollback_keeps_history_and_restores_previous_reference() -> None:
    reference_days = ReferenceDays(user_id=uuid7())
    first_day_id = uuid7()
    current_day_id = uuid7()
    reference_days.initialize(first_day_id, uuid7(), uuid7(), datetime.now(UTC))
    reference_days.apply_confirmed_change(
        uuid7(), current_day_id, ReferenceType.WORST, datetime.now(UTC)
    )

    restored_day_id = reference_days.rollback_current(
        ReferenceType.WORST, lambda day_id: day_id == first_day_id
    )

    assert restored_day_id == first_day_id
    assert reference_days.worst_day_id == first_day_id
    assert any(event.day_id == current_day_id for event in reference_days.history)

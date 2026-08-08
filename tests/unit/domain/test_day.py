from datetime import datetime

import pytest

from mood_tracker.domain.enums import DayStatus
from mood_tracker.domain.errors import IncompleteDay
from tests.factories import DayFactory, FieldFactory


def test_skipped_text_completes_step_without_creating_value(
    day_factory: DayFactory,
    field_factory: FieldFactory,
) -> None:
    day = day_factory.build()
    text_version = field_factory.text(user_id=day.user_id).current_version

    day.skip_text(text_version)

    assert day.has_completed_step(text_version.field_id)
    assert text_version.field_id not in day.response.answers


def test_completion_requires_each_active_field_step(
    day_factory: DayFactory,
    field_factory: FieldFactory,
    fixed_now: datetime,
) -> None:
    day = day_factory.build()
    state_field = field_factory.scale(user_id=day.user_id, is_core=True)
    text_field = field_factory.text(user_id=day.user_id)
    day.save_value(state_field.current_version, 5)
    with pytest.raises(IncompleteDay):
        day.complete((state_field.id, text_field.id), fixed_now)

    day.skip_text(text_field.current_version)
    day.complete((state_field.id, text_field.id), fixed_now)

    assert day.status is DayStatus.COMPLETE

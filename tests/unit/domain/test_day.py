from datetime import UTC, date, datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.entities.day import Day
from mood_tracker.domain.entities.field import (
    Field,
    FieldDisplayConfig,
    FieldVersion,
    ScaleConfig,
    TextConfig,
)
from mood_tracker.domain.enums import DayStatus, FieldStatus, FieldType
from mood_tracker.domain.errors import IncompleteDay
from mood_tracker.domain.policies.completion import CompletionPolicy


def _field(version: FieldVersion) -> Field:
    return Field(
        id=version.field_id,
        user_id=uuid7(),
        name="Поле",
        status=FieldStatus.ACTIVE,
        is_core=version.type is FieldType.SCALE,
        sort_order=0,
        display_config=FieldDisplayConfig(),
        current_version=version,
    )


def test_skipped_text_completes_step_without_creating_value() -> None:
    day = Day(id=uuid7(), user_id=uuid7(), date=date(2026, 7, 27))
    text_version = FieldVersion(
        id=uuid7(),
        field_id=uuid7(),
        type=FieldType.TEXT,
        config=TextConfig(),
        created_at=datetime.now(UTC),
    )

    day.skip_text(text_version)

    assert day.has_completed_step(text_version.field_id)
    assert text_version.field_id not in day.values


def test_completion_requires_each_active_field_step() -> None:
    day = Day(id=uuid7(), user_id=uuid7(), date=date(2026, 7, 27))
    state_version = FieldVersion(
        id=uuid7(),
        field_id=uuid7(),
        type=FieldType.SCALE,
        config=ScaleConfig(0, 10),
        created_at=datetime.now(UTC),
    )
    text_version = FieldVersion(
        id=uuid7(),
        field_id=uuid7(),
        type=FieldType.TEXT,
        config=TextConfig(),
        created_at=datetime.now(UTC),
    )
    fields = (_field(state_version), _field(text_version))

    day.save_value(state_version, 5)
    with pytest.raises(IncompleteDay):
        CompletionPolicy().complete(day, fields, datetime.now(UTC))

    day.skip_text(text_version)
    CompletionPolicy().complete(day, fields, datetime.now(UTC))

    assert day.status is DayStatus.COMPLETE

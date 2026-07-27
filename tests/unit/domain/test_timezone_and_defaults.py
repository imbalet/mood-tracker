from datetime import datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.enums import FieldType
from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.factories.defaults import (
    DefaultFieldIds,
    create_default_fields,
)
from mood_tracker.domain.value_objects.timezone import UserTimezone


def test_timezone_requires_iana_identifier() -> None:
    assert UserTimezone("Europe/Moscow").name == "Europe/Moscow"

    with pytest.raises(InvalidTimezone):
        UserTimezone("+03:00")


def test_default_field_factory_creates_expected_core_and_order(
    fixed_now: datetime,
) -> None:
    fields = create_default_fields(
        user_id=uuid7(),
        ids=DefaultFieldIds(*(uuid7() for _ in range(8))),
        created_at=fixed_now,
    )

    assert [field.name for field in fields] == [
        "Состояние",
        "Плач",
        "Негативные мысли",
        "Комментарий",
    ]
    assert fields[0].is_core
    assert fields[0].current_version.type is FieldType.SCALE
    assert fields[1].display_config.emoji == "💧"

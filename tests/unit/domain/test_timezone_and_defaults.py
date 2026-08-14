from datetime import UTC, date, datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.enums import (
    FieldType,
    QuestionnaireFieldRole,
)
from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.factories.defaults import (
    DefaultProfileIds,
    create_default_profile_setup,
)
from mood_tracker.domain.value_objects.timezone import UserTimezone


def test_timezone_requires_iana_identifier() -> None:
    assert UserTimezone("Europe/Moscow").name == "Europe/Moscow"

    with pytest.raises(InvalidTimezone):
        UserTimezone("+03:00")


def test_timezone_calculates_local_date_from_utc_instant() -> None:
    timezone = UserTimezone("Asia/Vladivostok")

    assert timezone.local_date_at(datetime(2025, 1, 2, 16, tzinfo=UTC)) == date(
        2025, 1, 3
    )


def test_default_field_factory_creates_expected_core_and_order(
    fixed_now: datetime,
) -> None:
    user_id = uuid7()
    ids = DefaultProfileIds.generate(uuid7)
    setup = create_default_profile_setup(
        user_id=user_id,
        ids=ids,
        created_at=fixed_now,
    )
    fields = setup.fields

    assert [field.name for field in fields] == [
        "Состояние",
        "Негативные мысли",
        "Комментарий",
        "Описание",
    ]
    questionnaires = setup.questionnaires
    assert (
        questionnaires[0].fields[fields[0].id].role is QuestionnaireFieldRole.DAY_STATE
    )
    assert fields[0].current_version.type is FieldType.SCALE
    assert fields[1].display_config.emoji == "💀"

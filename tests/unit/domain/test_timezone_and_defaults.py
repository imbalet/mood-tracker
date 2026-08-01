from datetime import datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.enums import (
    FieldType,
    QuestionnaireFieldRole,
)
from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.factories.defaults import (
    DefaultFieldIds,
    create_default_fields,
    create_default_questionnaires,
)
from mood_tracker.domain.value_objects.timezone import UserTimezone


def test_timezone_requires_iana_identifier() -> None:
    assert UserTimezone("Europe/Moscow").name == "Europe/Moscow"

    with pytest.raises(InvalidTimezone):
        UserTimezone("+03:00")


def test_default_field_factory_creates_expected_core_and_order(
    fixed_now: datetime,
) -> None:
    user_id = uuid7()
    ids = DefaultFieldIds(*(uuid7() for _ in range(8)))
    fields = create_default_fields(
        user_id=user_id,
        ids=ids,
        created_at=fixed_now,
    )

    assert [field.name for field in fields] == [
        "Состояние",
        "Негативные мысли",
        "Комментарий",
        "Описание",
    ]
    questionnaires = create_default_questionnaires(user_id, uuid7(), uuid7(), ids)
    assert (
        questionnaires[0].fields[fields[0].id].role is QuestionnaireFieldRole.DAY_STATE
    )
    assert fields[0].current_version.type is FieldType.SCALE
    assert fields[1].display_config.emoji == "💀"

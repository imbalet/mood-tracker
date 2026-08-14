from datetime import UTC, datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.entities.field import (
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import FieldType, QuestionnaireFieldRole
from mood_tracker.domain.errors import CoreFieldViolation, InvalidFieldVersion
from tests.factories import FieldFactory


def test_ordinal_config_accepts_sequential_values_without_zero() -> None:
    config = OrdinalConfig((OrdinalOption(1, "Мало"), OrdinalOption(2, "Много")))

    assert config.normalize(1) == 0.0
    assert config.normalize(2) == 1.0


def test_ordinal_config_rejects_non_sequential_values() -> None:
    with pytest.raises(InvalidFieldVersion):
        OrdinalConfig((OrdinalOption(0, "Нет"), OrdinalOption(2, "Много")))


def test_field_version_is_immutable(field_factory: FieldFactory) -> None:
    version = field_factory.scale().current_version

    with pytest.raises(AttributeError):
        version.config = ScaleConfig(0, 5)  # type: ignore[misc]


def test_field_version_derives_type_from_config() -> None:
    version = FieldVersion(
        id=uuid7(),
        field_id=uuid7(),
        config=ScaleConfig(0, 10),
        created_at=datetime.now(UTC),
    )

    assert version.type is FieldType.SCALE


def test_field_rejects_new_version_of_another_type(
    field_factory: FieldFactory,
) -> None:
    field = field_factory.text()
    version = FieldVersion(
        id=uuid7(),
        field_id=field.id,
        config=ScaleConfig(0, 10),
        created_at=datetime.now(UTC),
    )

    with pytest.raises(InvalidFieldVersion):
        field.add_version(version)


def test_core_field_cannot_be_hidden(field_factory: FieldFactory) -> None:
    field = field_factory.scale(is_core=True)
    placement = QuestionnaireField(field.id, 0, role=QuestionnaireFieldRole.DAY_STATE)

    with pytest.raises(CoreFieldViolation):
        placement.set_enabled(False)


def test_event_description_cannot_be_hidden(field_factory: FieldFactory) -> None:
    placement = QuestionnaireField(
        field_factory.text().id,
        0,
        role=QuestionnaireFieldRole.EVENT_DESCRIPTION,
    )

    with pytest.raises(CoreFieldViolation):
        placement.set_enabled(False)

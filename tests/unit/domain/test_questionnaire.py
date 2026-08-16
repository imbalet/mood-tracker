from datetime import UTC, datetime
from uuid import uuid7

import pytest

from mood_tracker.domain.entities import Questionnaire
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    MoveDirection,
    QuestionnaireFieldRole,
    QuestionnaireKind,
)
from mood_tracker.domain.errors import CoreFieldViolation, QuestionnaireViolation


def test_questionnaire_attaches_fields_in_order_and_rejects_duplicates() -> None:
    questionnaire = Questionnaire(uuid7(), uuid7(), QuestionnaireKind.DAY)
    first = questionnaire.attach(uuid7(), is_required=True)
    second = questionnaire.attach(uuid7())

    assert [placement.sort_order for placement in questionnaire.ordered_fields()] == [
        0,
        1,
    ]
    assert first.is_required
    assert not second.is_required

    with pytest.raises(QuestionnaireViolation):
        questionnaire.attach(first.field_id)


def test_questionnaire_delete_keeps_absolute_order_and_restore_reenables() -> None:
    questionnaire = Questionnaire(uuid7(), uuid7(), QuestionnaireKind.DAY)
    first = questionnaire.attach(uuid7())
    second = questionnaire.attach(uuid7())
    third = questionnaire.attach(uuid7())

    deleted_at = datetime(2025, 1, 1, tzinfo=UTC)
    questionnaire.delete(second.field_id, deleted_at)
    questionnaire.move(third.field_id, MoveDirection.UP)

    assert [placement.field_id for placement in questionnaire.ordered_fields()] == [
        third.field_id,
        second.field_id,
        first.field_id,
    ]
    assert [placement.sort_order for placement in questionnaire.ordered_fields()] == [
        0,
        1,
        2,
    ]
    assert questionnaire.fields[second.field_id].deleted_at == deleted_at

    restored = questionnaire.attach(second.field_id)

    assert restored.is_enabled
    assert restored.deleted_at is None
    assert restored.sort_order == 1


def test_questionnaire_rejects_invalid_placement_state() -> None:
    field_id = uuid7()

    with pytest.raises(QuestionnaireViolation):
        Questionnaire(
            uuid7(),
            uuid7(),
            QuestionnaireKind.DAY,
            {uuid7(): QuestionnaireField(field_id, 0)},
        )

    with pytest.raises(QuestionnaireViolation):
        Questionnaire(
            uuid7(),
            uuid7(),
            QuestionnaireKind.DAY,
            {field_id: QuestionnaireField(field_id, 1)},
        )

    with pytest.raises(QuestionnaireViolation):
        Questionnaire(uuid7(), uuid7(), QuestionnaireKind.EVENT).attach(
            field_id, role=QuestionnaireFieldRole.DAY_STATE
        )


def test_questionnaire_protects_system_placements() -> None:
    questionnaire = Questionnaire(uuid7(), uuid7(), QuestionnaireKind.DAY)
    core = questionnaire.attach(
        uuid7(), role=QuestionnaireFieldRole.DAY_STATE, is_required=True
    )

    with pytest.raises(CoreFieldViolation):
        questionnaire.delete(core.field_id, datetime(2025, 1, 1, tzinfo=UTC))
    with pytest.raises(CoreFieldViolation):
        questionnaire.set_enabled(core.field_id, False)
    with pytest.raises(CoreFieldViolation):
        questionnaire.set_required(core.field_id, False)


def test_questionnaire_lists_enabled_and_required_fields_in_order() -> None:
    questionnaire = Questionnaire(uuid7(), uuid7(), QuestionnaireKind.DAY)
    first = questionnaire.attach(uuid7(), is_required=True)
    second = questionnaire.attach(uuid7(), is_required=False)
    third = questionnaire.attach(uuid7(), is_required=True)
    questionnaire.set_enabled(second.field_id, False)

    assert questionnaire.enabled_field_ids() == (first.field_id, third.field_id)
    assert questionnaire.required_enabled_field_ids() == (
        first.field_id,
        third.field_id,
    )


def test_questionnaire_returns_its_single_system_field_id() -> None:
    questionnaire = Questionnaire(uuid7(), uuid7(), QuestionnaireKind.EVENT)
    description = questionnaire.attach(
        uuid7(), role=QuestionnaireFieldRole.EVENT_DESCRIPTION
    )

    assert (
        questionnaire.system_field_id(QuestionnaireFieldRole.EVENT_DESCRIPTION)
        == description.field_id
    )

    with pytest.raises(QuestionnaireViolation):
        questionnaire.system_field_id(QuestionnaireFieldRole.DAY_STATE)

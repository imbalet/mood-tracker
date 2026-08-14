from unittest.mock import AsyncMock
from uuid import uuid7

import pytest

from mood_tracker.application.contracts.questionnaires import (
    AddFieldVersion,
    AttachFieldToQuestionnaire,
    CreateField,
    DeleteField,
    DetachFieldFromQuestionnaire,
    MoveQuestionnaireField,
    SetQuestionnaireFieldEnabled,
    SetQuestionnaireFieldRequired,
)
from mood_tracker.application.use_cases import (
    AddFieldVersionUseCase,
    AttachFieldToQuestionnaireUseCase,
    CreateFieldUseCase,
    DeleteFieldUseCase,
    DetachFieldFromQuestionnaireUseCase,
    MoveQuestionnaireFieldUseCase,
    SetQuestionnaireFieldEnabledUseCase,
    SetQuestionnaireFieldRequiredUseCase,
)
from mood_tracker.domain.entities import (
    FieldDisplayConfig,
    Questionnaire,
    ScaleConfig,
    TextConfig,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    MoveDirection,
    QuestionnaireFieldRole,
    QuestionnaireKind,
)
from mood_tracker.domain.errors import CoreFieldViolation, InvalidFieldVersion


async def test_create_field_persists_current_semantic_version(
    uow, clock, id_generator, user_factory
) -> None:
    user = user_factory.build()
    uow.users.get = AsyncMock(return_value=user)
    uow.questionnaires.get = AsyncMock(
        return_value=Questionnaire(uuid7(), user.id, QuestionnaireKind.DAY)
    )
    use_case = CreateFieldUseCase(uow, clock, id_generator)

    field = await use_case.execute(
        CreateField(
            user_id=user.id,
            name="События дня",
            config=TextConfig(),
            display_config=FieldDisplayConfig(),
        )
    )

    assert field.current_version.config == TextConfig()
    uow.fields.add.assert_awaited_once_with(field)
    uow.commit.assert_awaited_once()


async def test_create_field_attaches_to_selected_questionnaire(
    uow, clock, id_generator, user_factory
) -> None:
    user = user_factory.build()
    questionnaire = Questionnaire(uuid7(), user.id, QuestionnaireKind.EVENT)
    uow.users.get = AsyncMock(return_value=user)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    field = await CreateFieldUseCase(uow, clock, id_generator).execute(
        CreateField(
            user_id=user.id,
            name="Контекст",
            config=TextConfig(),
            display_config=FieldDisplayConfig(),
            kind=QuestionnaireKind.EVENT,
        )
    )

    assert field.id in questionnaire.fields
    uow.questionnaires.get.assert_awaited_once_with(user.id, QuestionnaireKind.EVENT)


async def test_attach_field_to_questionnaire_uses_execute(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    questionnaire = Questionnaire(uuid7(), user.id, QuestionnaireKind.EVENT)
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    result = await AttachFieldToQuestionnaireUseCase(uow).execute(
        AttachFieldToQuestionnaire(user.id, field.id, QuestionnaireKind.EVENT)
    )

    assert result is field
    assert field.id in questionnaire.fields
    uow.questionnaires.save.assert_awaited_once_with(questionnaire)


async def test_detach_field_from_questionnaire_uses_execute(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    questionnaire = Questionnaire(
        uuid7(),
        user.id,
        QuestionnaireKind.DAY,
        {field.id: QuestionnaireField(field.id, 0)},
    )
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    result = await DetachFieldFromQuestionnaireUseCase(uow).execute(
        DetachFieldFromQuestionnaire(user.id, field.id, QuestionnaireKind.DAY)
    )

    assert result is field
    assert questionnaire.fields == {}
    uow.questionnaires.save.assert_awaited_once_with(questionnaire)


async def test_set_questionnaire_field_enabled_uses_execute(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    questionnaire = Questionnaire(
        uuid7(),
        user.id,
        QuestionnaireKind.DAY,
        {field.id: QuestionnaireField(field.id, 0)},
    )
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    result = await SetQuestionnaireFieldEnabledUseCase(uow).execute(
        SetQuestionnaireFieldEnabled(user.id, field.id, QuestionnaireKind.DAY, False)
    )

    assert result is field
    assert not questionnaire.fields[field.id].is_enabled
    uow.questionnaires.save.assert_awaited_once_with(questionnaire)


async def test_set_questionnaire_field_required_uses_execute(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    questionnaire = Questionnaire(
        uuid7(),
        user.id,
        QuestionnaireKind.DAY,
        {field.id: QuestionnaireField(field.id, 0)},
    )
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)

    result = await SetQuestionnaireFieldRequiredUseCase(uow).execute(
        SetQuestionnaireFieldRequired(user.id, field.id, QuestionnaireKind.DAY, False)
    )

    assert result is field
    assert not questionnaire.fields[field.id].is_required
    uow.questionnaires.save.assert_awaited_once_with(questionnaire)


async def test_move_field_swaps_neighbours_and_normalizes_order(
    uow, clock, user_factory, field_factory
) -> None:
    user = user_factory.build()
    first = field_factory.text(user_id=user.id, name="Первое")
    second = field_factory.text(user_id=user.id, name="Второе")
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.list_for_user = AsyncMock(return_value=(first, second))

    questionnaire = Questionnaire(
        uuid7(),
        user.id,
        QuestionnaireKind.DAY,
        {
            first.id: QuestionnaireField(first.id, 0),
            second.id: QuestionnaireField(second.id, 1),
        },
    )
    uow.questionnaires.get = AsyncMock(return_value=questionnaire)
    items = await MoveQuestionnaireFieldUseCase(uow).execute(
        MoveQuestionnaireField(
            user.id, second.id, QuestionnaireKind.DAY, MoveDirection.UP
        )
    )

    assert [item.field.name for item in items] == ["Второе", "Первое"]
    assert [item.placement.sort_order for item in items] == [
        0,
        1,
    ]
    uow.questionnaires.save.assert_awaited_once()
    uow.commit.assert_awaited_once()


async def test_add_field_version_rejects_type_change(
    uow, clock, id_generator, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    uow.fields.get = AsyncMock(return_value=field)

    with pytest.raises(InvalidFieldVersion):
        await AddFieldVersionUseCase(uow, clock, id_generator).execute(
            AddFieldVersion(user.id, field.id, ScaleConfig(0, 10))
        )

    uow.fields.save.assert_not_awaited()


async def test_delete_field_soft_deletes_an_ordinary_field(
    uow, clock, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.text(user_id=user.id)
    day_questionnaire = Questionnaire(uuid7(), user.id, QuestionnaireKind.DAY)
    event_questionnaire = Questionnaire(uuid7(), user.id, QuestionnaireKind.EVENT)
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(
        side_effect=(day_questionnaire, event_questionnaire)
    )

    await DeleteFieldUseCase(uow, clock).execute(DeleteField(user.id, field.id))

    assert field.deleted_at == clock.now()
    uow.fields.save.assert_awaited_once_with(field)


async def test_delete_field_rejects_a_system_placement(
    uow, clock, user_factory, field_factory
) -> None:
    user = user_factory.build()
    field = field_factory.scale(user_id=user.id)
    day_questionnaire = Questionnaire(
        uuid7(),
        user.id,
        QuestionnaireKind.DAY,
        {
            field.id: QuestionnaireField(
                field.id, 0, role=QuestionnaireFieldRole.DAY_STATE
            )
        },
    )
    event_questionnaire = Questionnaire(uuid7(), user.id, QuestionnaireKind.EVENT)
    uow.fields.get = AsyncMock(return_value=field)
    uow.questionnaires.get = AsyncMock(
        side_effect=(day_questionnaire, event_questionnaire)
    )

    with pytest.raises(CoreFieldViolation):
        await DeleteFieldUseCase(uow, clock).execute(DeleteField(user.id, field.id))

    uow.fields.save.assert_not_awaited()

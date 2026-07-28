from unittest.mock import AsyncMock

import pytest

from mood_tracker.application.commands import (
    AddFieldVersion,
    CreateField,
    MoveDirection,
    MoveField,
)
from mood_tracker.application.use_cases import (
    AddFieldVersionUseCase,
    CreateFieldUseCase,
    MoveFieldUseCase,
)
from mood_tracker.domain.entities import FieldDisplayConfig, ScaleConfig, TextConfig
from mood_tracker.domain.errors import InvalidFieldVersion


async def test_create_field_persists_current_semantic_version(
    uow, clock, id_generator, user_factory
) -> None:
    user = user_factory.build()
    uow.users.get = AsyncMock(return_value=user)
    use_case = CreateFieldUseCase(uow, clock, id_generator)

    field = await use_case.execute(
        CreateField(
            user_id=user.id,
            name="События дня",
            config=TextConfig(),
            display_config=FieldDisplayConfig(),
            sort_order=4,
        )
    )

    assert field.current_version.config == TextConfig()
    uow.fields.add.assert_awaited_once_with(field)
    uow.commit.assert_awaited_once()


async def test_move_field_swaps_neighbours_and_normalizes_order(
    uow, user_factory, field_factory
) -> None:
    user = user_factory.build()
    first = field_factory.text(user_id=user.id, name="Первое", sort_order=3)
    second = field_factory.text(user_id=user.id, name="Второе", sort_order=8)
    uow.users.get = AsyncMock(return_value=user)
    uow.fields.list_for_user = AsyncMock(return_value=(first, second))

    fields = await MoveFieldUseCase(uow).execute(
        MoveField(user.id, second.id, MoveDirection.UP)
    )

    assert [field.name for field in fields] == ["Второе", "Первое"]
    assert [field.sort_order for field in fields] == [0, 1]
    assert uow.fields.save.await_count == 2
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

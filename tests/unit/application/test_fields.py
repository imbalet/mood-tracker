from unittest.mock import AsyncMock

from mood_tracker.application.commands import CreateField
from mood_tracker.application.use_cases import CreateFieldUseCase
from mood_tracker.domain.entities import FieldDisplayConfig, TextConfig


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

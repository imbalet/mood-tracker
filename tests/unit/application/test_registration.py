from unittest.mock import AsyncMock

from mood_tracker.application.contracts.users import RegisterUser
from mood_tracker.application.errors import IdentifierCollision
from mood_tracker.application.use_cases import RegisterUserUseCase
from mood_tracker.domain.value_objects import UserTimezone


async def test_register_user_creates_default_profile_and_fields(
    uow, clock, id_generator
) -> None:
    uow.users.get_by_telegram_id = AsyncMock(return_value=None)
    use_case = RegisterUserUseCase(uow, clock, id_generator)

    user = await use_case.execute(RegisterUser(42, UserTimezone("Europe/Moscow")))

    assert user.telegram_id == 42
    uow.users.add.assert_awaited_once_with(user)
    assert uow.fields.add.await_count == 4
    uow.commit.assert_awaited_once()


async def test_register_user_retries_after_identifier_collision(
    uow, clock, id_generator
) -> None:
    uow.users.get_by_telegram_id = AsyncMock(side_effect=[None, None])
    uow.commit = AsyncMock(side_effect=[IdentifierCollision(), None])
    use_case = RegisterUserUseCase(uow, clock, id_generator)

    await use_case.execute(RegisterUser(42, UserTimezone("Europe/Moscow")))

    assert uow.users.add.await_count == 2
    assert uow.commit.await_count == 2

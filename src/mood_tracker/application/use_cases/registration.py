"""User registration and profile-settings use cases."""

from mood_tracker.application.commands import (
    GetUserByTelegramId,
    RegisterUser,
    SetTimezone,
)
from mood_tracker.application.errors import UserNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import UserProfile
from mood_tracker.domain.factories import (
    DefaultFieldIds,
    create_default_fields,
    create_default_questionnaires,
)


class RegisterUserUseCase:
    """Create an idempotent profile with the standard fields."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: RegisterUser) -> UserProfile:
        """Return an existing user or atomically create their default profile."""

        async def operation() -> UserProfile:
            existing = await self._uow.users.get_by_telegram_id(command.telegram_id)
            if existing is not None:
                return existing
            user = UserProfile(
                id=self._id_generator.new(),
                telegram_id=command.telegram_id,
                timezone=command.timezone,
            )
            ids = DefaultFieldIds(*(self._id_generator.new() for _ in range(8)))
            fields = create_default_fields(user.id, ids, self._clock.now())
            questionnaires = create_default_questionnaires(
                user.id, self._id_generator.new(), self._id_generator.new(), ids
            )
            await self._uow.users.add(user)
            for field in fields:
                await self._uow.fields.add(field)
            for questionnaire in questionnaires:
                await self._uow.questionnaires.add(questionnaire)
            return user

        return await execute_write(self._uow, operation)


class GetUserByTelegramIdUseCase:
    """Read the profile associated with one Telegram account."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: GetUserByTelegramId) -> UserProfile | None:
        """Return a profile without exposing any unrelated user data."""
        async with self._uow:
            return await self._uow.users.get_by_telegram_id(command.telegram_id)


class SetTimezoneUseCase:
    """Change the timezone used for user-local dates and reminders."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SetTimezone) -> UserProfile:
        """Persist a validated timezone change."""

        async def operation() -> UserProfile:
            user = await self._uow.users.get(command.user_id)
            if user is None:
                raise UserNotFound
            user.set_timezone(command.timezone)
            await self._uow.users.save(user)
            return user

        return await execute_transaction(self._uow, operation)

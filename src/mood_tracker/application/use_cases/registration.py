"""User registration and profile-settings use cases."""

from datetime import time, timedelta

from mood_tracker.application.contracts.users import (
    GetUserByTelegramId,
    RegisterUser,
    SetReminderSettings,
    SetTimezone,
)
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import require_user
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import NotificationSettings, UserProfile
from mood_tracker.domain.factories import (
    DefaultProfileIds,
    create_default_profile_setup,
)


class RegisterUserUseCase:
    """Create a profile with the standard fields."""

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
            ids = DefaultProfileIds.generate(self._id_generator.new)
            setup = create_default_profile_setup(
                user_id=user.id, ids=ids, created_at=self._clock.now()
            )
            fields = setup.fields
            questionnaires = setup.questionnaires
            await self._uow.users.add(user)
            # TODO: maybe refactor
            for field in fields:
                await self._uow.fields.add(field)
            for questionnaire in questionnaires:
                await self._uow.questionnaires.add(questionnaire)
            # TODO: посмотреть слоп
            await self._uow.notification_settings.add(
                NotificationSettings(
                    user_id=user.id,
                    is_enabled=False,
                    reminder_time=time(20),
                    repeat_interval=timedelta(days=1),
                    max_reminders_per_day=1,
                )
            )
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
            user = await require_user(self._uow, command.user_id)
            user.set_timezone(command.timezone)
            await self._uow.users.save(user)
            return user

        return await execute_transaction(self._uow, operation)


# TODO: посмотреть слоп
class SetReminderSettingsUseCase:
    """Persist validated reminder preferences for one user."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SetReminderSettings) -> NotificationSettings:
        async def operation() -> NotificationSettings:
            await require_user(self._uow, command.user_id)
            if command.max_reminders_per_day < 1:
                raise ValueError("max_reminders_per_day must be positive")
            if command.repeat_interval <= timedelta(0):
                raise ValueError("repeat_interval must be positive")
            settings = await self._uow.notification_settings.get(command.user_id)
            if settings is None:
                settings = NotificationSettings(
                    user_id=command.user_id,
                    is_enabled=command.is_enabled,
                    reminder_time=command.reminder_time,
                    repeat_interval=command.repeat_interval,
                    max_reminders_per_day=command.max_reminders_per_day,
                )
                await self._uow.notification_settings.add(settings)
            else:
                settings.is_enabled = command.is_enabled
                settings.reminder_time = command.reminder_time
                settings.repeat_interval = command.repeat_interval
                settings.max_reminders_per_day = command.max_reminders_per_day
                await self._uow.notification_settings.save(settings)
            return settings

        return await execute_transaction(self._uow, operation)

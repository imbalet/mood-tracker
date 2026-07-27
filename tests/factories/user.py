"""Builder for valid user profiles."""

from uuid import UUID, uuid7

from mood_tracker.domain.entities import UserProfile
from mood_tracker.domain.value_objects import UserTimezone


class UserFactory:
    """Build user profiles with explicit overrides for each test."""

    def build(
        self,
        *,
        id: UUID | None = None,
        telegram_id: int = 123_456_789,
        timezone: UserTimezone | str = "Europe/Moscow",
    ) -> UserProfile:
        """Build a valid user profile."""
        return UserProfile(
            id=id or uuid7(),
            telegram_id=telegram_id,
            timezone=(
                timezone
                if isinstance(timezone, UserTimezone)
                else UserTimezone(timezone)
            ),
        )

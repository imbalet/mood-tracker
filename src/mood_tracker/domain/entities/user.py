"""User profile aggregate for durable account-level settings."""

from dataclasses import dataclass
from uuid import UUID

from mood_tracker.domain.value_objects import UserTimezone


@dataclass(slots=True)
class UserProfile:
    """A Telegram user's identity and current personal timezone."""

    id: UUID
    telegram_id: int
    timezone: UserTimezone

    def set_timezone(self, timezone: UserTimezone) -> None:
        """Change the timezone used for future user-local operations."""
        self.timezone = timezone

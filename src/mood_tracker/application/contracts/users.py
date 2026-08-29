"""User-related application contracts."""

from dataclasses import dataclass
from datetime import time, timedelta
from uuid import UUID

from mood_tracker.domain.value_objects import UserTimezone


@dataclass(frozen=True, slots=True)
class RegisterUser:
    """Register a Telegram user or return their existing profile."""

    telegram_id: int
    timezone: UserTimezone


@dataclass(frozen=True, slots=True)
class GetUserByTelegramId:
    """Look up a profile owned by a Telegram account."""

    telegram_id: int


@dataclass(frozen=True, slots=True)
class SetTimezone:
    """Change one user's IANA timezone."""

    user_id: UUID
    timezone: UserTimezone


@dataclass(frozen=True, slots=True)
class SetReminderSettings:
    """Change reminder delivery preferences for one user."""

    user_id: UUID
    is_enabled: bool
    reminder_time: time
    repeat_interval: timedelta
    max_reminders_per_day: int

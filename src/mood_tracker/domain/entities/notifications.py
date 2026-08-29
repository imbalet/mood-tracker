from dataclasses import dataclass
from datetime import time, timedelta
from uuid import UUID


@dataclass(kw_only=True)
class NotificationSettings:
    user_id: UUID
    is_enabled: bool
    reminder_time: time
    repeat_interval: timedelta
    max_reminders_per_day: int

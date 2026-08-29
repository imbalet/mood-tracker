"""Outbound notification delivery boundary."""

from typing import Protocol

from mood_tracker.domain.entities import UserProfile


class NotificationSender(Protocol):
    async def send_daily_reminder(self, user: UserProfile) -> None: ...

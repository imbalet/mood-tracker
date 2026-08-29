from datetime import time, timedelta
from unittest.mock import AsyncMock

from mood_tracker.application.ports import NotificationDeliveryStatus
from mood_tracker.application.ports.repositories import NotificationDelivery
from mood_tracker.application.use_cases import ProcessReminderUseCase
from mood_tracker.domain.entities import NotificationSettings
from mood_tracker.domain.enums import DayStatus
from mood_tracker.domain.reminder_policy import ReminderPolicy


async def test_process_reminder_claims_sends_and_marks_delivery(
    uow, user_factory, clock
) -> None:
    user = user_factory.build()
    sender = AsyncMock()
    uow.users.get = AsyncMock(return_value=user)
    uow.notification_settings.get = AsyncMock(
        return_value=NotificationSettings(
            user_id=user.id,
            is_enabled=True,
            reminder_time=time(10),
            repeat_interval=timedelta(hours=2),
            max_reminders_per_day=2,
        )
    )
    uow.days.get_by_date = AsyncMock(return_value=None)
    uow.notification_deliveries.get_deliveries = AsyncMock(
        return_value=[NotificationDelivery(1, NotificationDeliveryStatus.sent)]
    )
    uow.notification_deliveries.try_claim = AsyncMock(return_value=True)
    uow.notification_deliveries.mark_sent = AsyncMock()

    await ProcessReminderUseCase(
        uow, sender, ReminderPolicy(timedelta(hours=4)), clock
    ).execute(user.id)

    sender.send_daily_reminder.assert_awaited_once_with(user)
    uow.notification_deliveries.try_claim.assert_awaited_once()
    uow.notification_deliveries.mark_sent.assert_awaited_once()
    assert uow.commit.await_count == 2


async def test_process_reminder_does_not_send_for_completed_day(
    uow, user_factory, day_factory, clock
) -> None:
    user = user_factory.build()
    sender = AsyncMock()
    uow.users.get = AsyncMock(return_value=user)
    uow.notification_settings.get = AsyncMock(
        return_value=NotificationSettings(
            user_id=user.id,
            is_enabled=True,
            reminder_time=time(10),
            repeat_interval=timedelta(hours=2),
            max_reminders_per_day=2,
        )
    )
    uow.days.get_by_date = AsyncMock(
        return_value=day_factory.build(user_id=user.id, status=DayStatus.COMPLETE)
    )
    uow.notification_deliveries.get_deliveries = AsyncMock(return_value=[])

    await ProcessReminderUseCase(
        uow, sender, ReminderPolicy(timedelta(minutes=30)), clock
    ).execute(user.id)

    sender.send_daily_reminder.assert_not_awaited()
    uow.notification_deliveries.try_claim.assert_not_awaited()

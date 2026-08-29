"""Evaluate and deliver one user's daily reminder."""

# TODO: посмотреть слоп

from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from mood_tracker.application.ports import (
    Clock,
    NotificationDeliveryStatus,
    NotificationSender,
    UnitOfWork,
)
from mood_tracker.application.use_cases._loaders import require_user
from mood_tracker.application.use_cases._transactions import execute_transaction
from mood_tracker.domain.enums import DayStatus
from mood_tracker.domain.reminder_policy import ReminderPolicy


class ProcessReminderUseCase:
    """Send at most one reminder that is due for a user's local calendar day."""

    _CLAIM_TIMEOUT = timedelta(minutes=10)

    def __init__(
        self,
        uow: UnitOfWork,
        notification_sender: NotificationSender,
        reminder_policy: ReminderPolicy,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._notification_sender = notification_sender
        self._reminder_policy = reminder_policy
        self._clock = clock

    async def execute(self, user_id: UUID) -> None:
        """Claim, send and finalize a due reminder.

        The claim is committed before contacting Telegram. A failed delivery
        therefore remains reclaimable after the timeout, while concurrent
        workers cannot send the same reminder at the same time.
        """
        now = self._clock.now()

        async with self._uow:
            user = await require_user(self._uow, user_id)
            settings = await self._uow.notification_settings.get(user.id)
            if settings is None or not settings.is_enabled:
                return

            local_now = now.astimezone(ZoneInfo(user.timezone.name))
            local_date = local_now.date()
            day = await self._uow.days.get_by_date(user.id, local_date)
            deliveries = await self._uow.notification_deliveries.get_deliveries(
                user.id, local_date
            )
            sent_reminders = {
                delivery.reminder_number
                for delivery in deliveries
                if delivery.status is NotificationDeliveryStatus.sent
            }
            decision = self._reminder_policy.evaluate(
                settings=settings,
                local_now=local_now.replace(tzinfo=None),
                local_date=local_date,
                sent_reminders=sent_reminders,
                mood_entry_exists=day is not None and day.status is DayStatus.COMPLETE,
            )
            reminder_number = decision.reminder_number
            if reminder_number is None:
                return

            claimed = await self._uow.notification_deliveries.try_claim(
                user.id,
                local_date,
                reminder_number,
                self._CLAIM_TIMEOUT,
            )
            if not claimed:
                return
            await self._uow.commit()

        await self._notification_sender.send_daily_reminder(user)

        async def mark_sent() -> None:
            await self._uow.notification_deliveries.mark_sent(
                user.id, local_date, reminder_number, now
            )

        await execute_transaction(self._uow, mark_sent)

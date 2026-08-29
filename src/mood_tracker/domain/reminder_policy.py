from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from mood_tracker.domain.entities import NotificationSettings

# TODO: посмотреть слоп


@dataclass(frozen=True)
class ReminderDecision:
    reminder_number: int | None


class ReminderPolicy:
    def __init__(self, grace_period: timedelta) -> None:
        self._grace_period = grace_period

    def evaluate(
        self,
        settings: NotificationSettings,
        local_now: datetime,
        local_date: date,
        sent_reminders: set[int],
        mood_entry_exists: bool,
    ) -> ReminderDecision:
        if not settings.is_enabled:
            return ReminderDecision(None)

        if mood_entry_exists:
            return ReminderDecision(None)

        for reminder_number in range(1, settings.max_reminders_per_day + 1):
            if reminder_number in sent_reminders:
                continue

            scheduled_at = self._get_scheduled_at(
                local_date,
                reminder_number,
                settings.reminder_time,
                settings.repeat_interval,
            )

            # Ещё рано для этого reminder.
            if scheduled_at > local_now:
                return ReminderDecision(None)

            # Окно отправки ещё не закончилось.
            if local_now <= scheduled_at + self._grace_period:
                return ReminderDecision(reminder_number)

            # Опоздали — это reminder уже потерян.
            # Ищем следующий.
            continue

        return ReminderDecision(None)

    @staticmethod
    def _get_scheduled_at(
        local_date: date,
        reminder_number: int,
        reminder_time: time,
        repeat_interval: timedelta,
    ) -> datetime:
        return (
            datetime.combine(local_date, reminder_time)
            + (reminder_number - 1) * repeat_interval
        )

"""Personalized inline date picker built on aiogram-calendar callbacks."""

import calendar
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_calendar import SimpleCalendar
from aiogram_calendar.schemas import SimpleCalAct, SimpleCalendarCallback

from mood_tracker.domain.enums import DayStatus

_WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_MONTHS = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)


class MoodDateCalendar(SimpleCalendar):  # type: ignore[misc]
    """SimpleCalendar navigation with diary-status labels and local-date bounds."""

    def __init__(self, today: date, statuses: dict[date, DayStatus]) -> None:
        super().__init__(cancel_btn="В меню", today_btn="Сегодня")
        self._today = today
        self._statuses = statuses
        self.set_dates_range(date.min, today)

    async def start_calendar(self, year: int, month: int) -> InlineKeyboardMarkup:
        """Build a Russian month keyboard while preserving package callback data."""
        keyboard: list[list[InlineKeyboardButton]] = [
            [
                self._button("<<", SimpleCalAct.prev_y, year, month),
                InlineKeyboardButton(
                    text=str(year), callback_data=self.ignore_callback
                ),
                self._button(">>", SimpleCalAct.next_y, year, month),
            ],
            [
                self._button("<", SimpleCalAct.prev_m, year, month),
                InlineKeyboardButton(
                    text=_MONTHS[month - 1], callback_data=self.ignore_callback
                ),
                self._button(">", SimpleCalAct.next_m, year, month),
            ],
            [
                InlineKeyboardButton(text=weekday, callback_data=self.ignore_callback)
                for weekday in _WEEKDAYS
            ],
        ]
        for week in calendar.monthcalendar(year, month):
            row: list[InlineKeyboardButton] = []
            for day_number in week:
                if day_number == 0:
                    row.append(
                        InlineKeyboardButton(
                            text=" ", callback_data=self.ignore_callback
                        )
                    )
                    continue
                target = date(year, month, day_number)
                row.append(
                    InlineKeyboardButton(
                        text=_label(target, self._statuses.get(target)),
                        callback_data=SimpleCalendarCallback(
                            act=SimpleCalAct.day,
                            year=year,
                            month=month,
                            day=day_number,
                        ).pack(),
                    )
                )
            keyboard.append(row)
        keyboard.append(
            [
                self._button("В меню", SimpleCalAct.cancel, year, month),
                InlineKeyboardButton(text=" ", callback_data=self.ignore_callback),
                self._button("Сегодня", SimpleCalAct.today, year, month),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def _button(
        self, text: str, action: SimpleCalAct, year: int, month: int
    ) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=text,
            callback_data=SimpleCalendarCallback(
                act=action, year=year, month=month, day=1
            ).pack(),
        )


def _label(target: date, status: DayStatus | None) -> str:
    if status is DayStatus.COMPLETE:
        return f"✅ {target.day}"
    if status is DayStatus.DRAFT:
        return f"📝 {target.day}"
    return str(target.day)

"""Rich Telegram screen for the rendered diary calendar."""

from dataclasses import dataclass
from datetime import date
from typing import ClassVar, override

from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichMessage,
)
from aiogram.types.input_rich_message_media import InputRichMessageMedia

from mood_tracker.application.contracts.calendar import MonthCalendar
from mood_tracker.presentation.callbacks.callbacks import (
    CalendarImageAction,
    CalendarImageCallback,
    MenuCallback,
    MenuSection,
)
from mood_tracker.presentation.keyboards.date_calendar import MoodDateCalendar
from mood_tracker.presentation.screens.screen import Screen, ScreenContent


@dataclass
class CalendarScreen(Screen):
    text: ClassVar[str | None] = "<b>Выбери дату</b>\n✅ — завершён, 📝 — черновик."
    data: MonthCalendar
    today: date
    month: date

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        statuses = {day.date: day.status for day in self.data.days}
        calendar = MoodDateCalendar(self.today, statuses)
        return calendar.start_calendar(self.month.year, self.month.month)


@dataclass
class CalendarImageScreen(Screen):
    image: BufferedInputFile
    can_go_next: bool
    month: date

    @override
    def _text(self) -> ScreenContent:
        return InputRichMessage(
            html='<img src="tg://photo?id=calendar"/>',
            media=[
                InputRichMessageMedia(
                    id="calendar", media=InputMediaPhoto(media=self.image)
                )
            ],
        )

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            (
                "←",
                CalendarImageCallback(
                    action=CalendarImageAction.PREVIOUS,
                    year=self.month.year,
                    month=self.month.month,
                ),
            )
        )
        if self.can_go_next:
            self._kbuilder.row(
                (
                    "→",
                    CalendarImageCallback(
                        action=CalendarImageAction.NEXT,
                        year=self.month.year,
                        month=self.month.month,
                    ),
                )
            )

        self._kbuilder.row(("В меню", MenuCallback(section=MenuSection.HOME)))
        return self._kbuilder.as_markup()

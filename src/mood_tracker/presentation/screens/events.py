from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar, override
from uuid import UUID

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.application.contracts.questionnaires import (
    QuestionnaireFieldItem,
)
from mood_tracker.domain.entities import (
    Event,
    Field,
    OrdinalConfig,
    ScaleConfig,
    UserProfile,
)
from mood_tracker.domain.enums import EventStatus
from mood_tracker.presentation.callbacks.callbacks import (
    EventAction,
    EventCallback,
    EventTimeCallback,
    EventValueCallback,
    SkipEventFieldCallback,
)
from mood_tracker.presentation.screens.screen import Screen, ScreenContent


@dataclass
class ChooseEventCompleteScreen(Screen):
    text: ClassVar[str | None] = "Как записать событие?"
    date: date

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        return (
            self._kbuilder.row(
                (
                    "Заполнить анкету",
                    EventCallback(
                        action=EventAction.START, day=self.date.strftime("%Y%m%d")
                    ),
                )
            )
            .row(("Быстрый текст", EventCallback(action=EventAction.QUICK_TEXT)))
            .as_markup()
        )


@dataclass
class SendTextScreen(Screen):
    text: ClassVar[str | None] = "Отправь текст события."


@dataclass
class ChangeTimeScreen(Screen):
    text: ClassVar[str | None] = "Отправь новое время в формате <code>ЧЧ:ММ</code>."


@dataclass
class SetTimeScreen(Screen):
    text: ClassVar[str | None] = "Отправь новое время в формате <code>ЧЧ:ММ</code>."


@dataclass
class InvalidTimeScreen(Screen):
    text: ClassVar[str | None] = "Нужно время в формате <code>ЧЧ:ММ</code>."


@dataclass
class NonEmptyTextRequiredScreen(Screen):
    text: ClassVar[str | None] = "Отправь непустой текст."


@dataclass
class EventEmptyScreen(Screen):
    text: ClassVar[str | None] = "Событие не создано: ничего не заполнено."


@dataclass
class PromptTextScreen(Screen):
    item: QuestionnaireFieldItem
    event_id: UUID

    @override
    def _text(self) -> ScreenContent:
        return f"<b>{self.item.field.name}</b>\nОтправь текст."

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        if not self.item.placement.is_required:
            self._kbuilder.row(
                (
                    "Пропустить",
                    SkipEventFieldCallback(
                        event_id=self.event_id, field_id=self.item.field.id
                    ),
                )
            )
            return self._kbuilder.as_markup()
        return None


@dataclass
class PromptValueScreen(Screen):
    item: QuestionnaireFieldItem
    event_id: UUID

    @override
    def _text(self) -> ScreenContent:
        return f"<b>{self.item.field.name}</b>\nВыбери значение."

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        config = self.item.field.current_version.config
        if isinstance(config, ScaleConfig):
            choices = (
                (value, str(value))
                for value in range(config.minimum, config.maximum + 1)
            )
        if isinstance(config, OrdinalConfig):
            choices = ((option.value, option.label) for option in config.options)
        else:
            raise TypeError  # TODO: fix
        for value, label in choices:
            self._kbuilder.row(
                (
                    label,
                    EventValueCallback(
                        event_id=self.event_id, field_id=self.item.field.id, value=value
                    ),
                )
            )

        if not self.item.placement.is_required:
            self._kbuilder.row(
                (
                    "Пропустить",
                    SkipEventFieldCallback(
                        event_id=self.event_id, field_id=self.item.field.id
                    ),
                )
            )
            return self._kbuilder.as_markup()
        return None


@dataclass
class DeleteEventConfirmScreen(Screen):
    text: ClassVar[str | None] = "Удалить событие?"
    event_id: UUID

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        return self._kbuilder.row(
            (
                "Удалить",
                EventCallback(
                    action=EventAction.CONFIRM_DELETE, event_id=self.event_id
                ),
            )
        ).as_markup()


@dataclass
class AskTimeScreen(Screen):
    text: ClassVar[str | None] = "<b>Когда произошло событие?</b>"
    allow_now: bool
    day_date: date

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        if self.allow_now:
            # TODO: отрефакторить этот колбек, убрать там day_date для сегодня
            self._kbuilder.row(
                (
                    "Сейчас",
                    EventTimeCallback(day=self.day_date.strftime("%Y%m%d"), now=True),
                )
            )
        self._kbuilder.row(
            (
                "Указать время",
                EventTimeCallback(day=self.day_date.strftime("%Y%m%d"), now=False),
            )
        )
        return self._kbuilder.as_markup()


@dataclass
class EventScreen(Screen):
    # TODO: rename
    local: datetime
    current: Event
    items: tuple[QuestionnaireFieldItem, ...]
    profile: UserProfile

    # TODO: pass timezone, not a profile

    @override
    def _text(self) -> ScreenContent:
        lines = [
            "<b>Событие</b>",
            (
                f"{self.local:%d.%m.%Y %H:%M}"
                + (
                    f" ({self.current.occurred_timezone.name})"
                    if self.current.occurred_timezone != self.profile.timezone
                    else ""
                )
            ),
            f"Статус: {'черновик' if self.current.status is EventStatus.DRAFT else 'завершено'}",  # noqa: E501
        ]
        for item in self.items:
            value = self.current.response.answers.get(item.field.id)
            progress = self.current.response.progress.get(item.field.id)
            if value is not None:
                rendered_value = self._render_value(
                    item.field, value.value, value.field_version_id
                )
                lines.append(f"<b>{item.field.name}</b>: {rendered_value}")
            elif progress is not None and progress.skipped:
                lines.append(f"<b>{item.field.name}</b>: пропущено")

        return "\n".join(lines)

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        if self.current.status is EventStatus.DRAFT:
            self._kbuilder.row(
                (
                    "Продолжить",
                    EventCallback(
                        action=EventAction.CONTINUE, event_id=self.current.id
                    ),
                )
            )
        self._kbuilder.row(
            (
                "Изменить время",
                EventCallback(action=EventAction.CHANGE_TIME, event_id=self.current.id),
            ),
            (
                "Удалить",
                EventCallback(action=EventAction.DELETE, event_id=self.current.id),
            ),
        )
        return self._kbuilder.as_markup()

    @staticmethod
    def _render_value(field: Field, value: int | str, version_id: UUID) -> str:
        version = field.get_version(version_id)
        if version is None:
            return str(value)
        config = version.config
        if isinstance(config, OrdinalConfig) and isinstance(value, int):
            return next(
                (option.label for option in config.options if option.value == value),
                str(value),
            )
        if isinstance(config, ScaleConfig):
            return f"{value}/{config.maximum}"
        return str(value)

from dataclasses import dataclass
from enum import StrEnum
from html import escape
from typing import ClassVar, override
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup

from mood_tracker.application.contracts.diary import DayForm, ReferenceReview
from mood_tracker.domain.entities import Event, Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import DayStatus, ReferenceType
from mood_tracker.presentation.callbacks.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    EventAction,
    EventCallback,
    MenuCallback,
    MenuSection,
    OpenDayCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens.screen import Screen, ScreenContent


class DayFieldAction(StrEnum):
    """One action a user may take from the day summary."""

    ADD = "add"
    EDIT = "edit"


class DayPromptKind(StrEnum):
    """Input control appropriate for a selected field."""

    CHOICES = "choices"
    TEXT = "text"


@dataclass(frozen=True, slots=True)
class DayCardView:
    """All display-ready data for one daily entry summary."""

    day: str
    date_label: str
    is_complete: bool
    entries: tuple[DayEntryView, ...]
    actions: tuple[DayFieldActionView, ...]
    events: tuple[DayEventView, ...] = ()


@dataclass(frozen=True, slots=True)
class DayEntryView:
    """One visible answered or skipped field on a day card."""

    name: str
    rendered_value: str | None
    emoji: str | None
    is_skipped: bool


@dataclass(frozen=True, slots=True)
class DayFieldActionView:
    """One field that can be added or edited from the card."""

    field_id: UUID
    name: str
    action: DayFieldAction


@dataclass(frozen=True, slots=True)
class DayEventView:
    event_id: UUID
    label: str


@dataclass(frozen=True, slots=True)
class DayValueOptionView:
    """One numeric answer choice shown on an inline keyboard."""

    value: int
    label: str


@dataclass(frozen=True, slots=True)
class DayValuePromptView:
    """A day card with one active answer prompt."""

    card: DayCardView
    field_id: UUID
    field_name: str
    kind: DayPromptKind
    options: tuple[DayValueOptionView, ...]


@dataclass
class DayCardScreen(Screen):
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 1

    form: DayForm
    events: tuple[Event, ...] = ()

    @staticmethod
    def _render_value(value: int | str, config: object) -> str:
        if isinstance(config, OrdinalConfig) and isinstance(value, int):
            return next(
                (option.label for option in config.options if option.value == value),
                str(value),
            )
        if isinstance(config, ScaleConfig):
            return f"{value}/{config.maximum}"
        return str(value)

    @staticmethod
    def _entry_views(form: DayForm) -> list[DayEntryView]:
        if form.day is None:
            return []
        entries: list[DayEntryView] = []
        for field in form.fields:
            value = form.day.response.answers.get(field.id)
            progress = form.day.response.progress.get(field.id)
            if value is None and progress is None:
                continue
            if value is None:
                entries.append(
                    DayEntryView(
                        name=field.name,
                        rendered_value=None,
                        emoji=field.display_config.emoji,
                        is_skipped=True,
                    )
                )
                continue
            version = field.get_version(value.field_version_id)
            if version is None:
                continue
            entries.append(
                DayEntryView(
                    name=field.name,
                    rendered_value=DayCardScreen._render_value(
                        value.value, version.config
                    ),
                    emoji=field.display_config.emoji,
                    is_skipped=False,
                )
            )
        return entries

    @staticmethod
    def _action_views(form: DayForm) -> list[DayFieldActionView]:
        actions: list[DayFieldActionView] = []
        for field in form.fields:
            placement = form.placements.get(field.id)
            if placement is None:
                continue
            is_completed = form.day is not None and form.day.has_completed_step(
                field.id
            )
            if is_completed:
                action = DayFieldAction.EDIT
            elif placement.is_enabled:
                action = DayFieldAction.ADD
            else:
                continue
            actions.append(DayFieldActionView(field.id, field.name, action))
        return actions

    @override
    def _text(self) -> ScreenContent:
        is_complete = (
            self.form.day is not None and self.form.day.status is DayStatus.COMPLETE
        )
        date_label = self.form.day_date.strftime("%d.%m.%Y")
        entries = self._entry_views(self.form)

        status = TextKey.DAY_COMPLETE if is_complete else TextKey.DAY_DRAFT
        lines = [f"<b>{date_label}</b> · {TEXTS[status]}"]
        if not entries:
            lines.append(TEXTS[TextKey.EMPTY_DAY])
            return "\n\n".join(lines)
        for entry in entries:
            emoji = f"{entry.emoji} " if entry.emoji else ""
            value = (
                TEXTS[TextKey.DAY_SKIPPED]
                if entry.is_skipped
                else escape(entry.rendered_value or "")
            )
            lines.append(f"{emoji}<b>{escape(entry.name)}</b>: {value}")
        return "\n".join(lines)

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        actions = self._action_views(self.form)
        day = self.form.day_date.strftime("%Y%m%d")
        actions = self._action_views(self.form)
        events = tuple(
            DayEventView(
                event.id,
                (
                    f"{'⏳ ' if event.status.value == 'draft' else ''}"
                    f"{event.occurred_at.astimezone(ZoneInfo(event.occurred_timezone.name)):%H:%M}"
                ),
            )
            for event in self.events
        )

        for action in actions:
            text = TEXTS[
                TextKey.EDIT_FIELD
                if action.action is DayFieldAction.EDIT
                else TextKey.ADD_FIELD_VALUE
            ].format(name=action.name)
            self._kbuilder.row(
                (text, EditDayValueCallback(day=day, field_id=action.field_id))
            )
        for item in events:
            self._kbuilder.row(
                (
                    item.label,
                    EventCallback(action=EventAction.OPEN, event_id=item.event_id),
                )
            )
        self._kbuilder.row(
            (
                "＋ Добавить событие",
                EventCallback(action=EventAction.START, day=day),
            )
        ).row((TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME)))
        return self._kbuilder.as_markup()


@dataclass
class DayValuePromptScreen(Screen):
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 4

    view: DayValuePromptView
    error: str | None = None

    @staticmethod
    def _card_text(view: DayCardView) -> str:
        status = TextKey.DAY_COMPLETE if view.is_complete else TextKey.DAY_DRAFT
        lines = [f"<b>{view.date_label}</b> · {TEXTS[status]}"]
        if not view.entries:
            lines.append(TEXTS[TextKey.EMPTY_DAY])
            return "\n\n".join(lines)
        for entry in view.entries:
            emoji = f"{entry.emoji} " if entry.emoji else ""
            value = (
                TEXTS[TextKey.DAY_SKIPPED]
                if entry.is_skipped
                else escape(entry.rendered_value or "")
            )
            lines.append(f"{emoji}<b>{escape(entry.name)}</b>: {value}")
        return "\n".join(lines)

    @override
    def _text(self) -> ScreenContent:
        prompt = (
            TEXTS[TextKey.ENTER_TEXT].format(name=escape(self.view.field_name))
            if self.view.kind is DayPromptKind.TEXT
            else TEXTS[TextKey.SELECT_VALUE].format(name=escape(self.view.field_name))
        )
        parts = [self._card_text(self.view.card), self.error, prompt]

        return "\n\n".join(part for part in parts if part)

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        if self.view.kind is DayPromptKind.CHOICES:
            self._kbuilder.buttons_iterable(
                (
                    option.label,
                    DayValueCallback(
                        day=self.view.card.day,
                        field_id=self.view.field_id,
                        value=option.value,
                    ),
                )
                for option in self.view.options
            )
        else:
            self._kbuilder.row(
                (
                    TextKey.SKIP,
                    SkipTextCallback(
                        day=self.view.card.day, field_id=self.view.field_id
                    ),
                )
            )
        self._kbuilder.row(
            (TextKey.BACK_TO_DAY, OpenDayCallback(day=self.view.card.day))
        )
        return self._kbuilder.as_markup()


def make_day_card_view(form: DayForm, events: tuple[Event, ...] = ()) -> DayCardView:
    """Map a day aggregate into the values needed by its Telegram card."""
    entries = tuple(DayCardScreen._entry_views(form))
    actions = tuple(DayCardScreen._action_views(form))
    return DayCardView(
        day=form.day_date.strftime("%Y%m%d"),
        date_label=form.day_date.strftime("%d.%m.%Y"),
        is_complete=form.day is not None and form.day.status is DayStatus.COMPLETE,
        entries=entries,
        actions=actions,
        events=tuple(
            DayEventView(
                event.id,
                (
                    f"{'⏳ ' if event.status.value == 'draft' else ''}"
                    f"{event.occurred_at.astimezone(ZoneInfo(event.occurred_timezone.name)):%H:%M}"
                ),
            )
            for event in events
        ),
    )


def make_day_value_prompt_view(form: DayForm, field: Field) -> DayValuePromptView:
    """Map one current field configuration into an answer prompt."""
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        options = tuple(
            DayValueOptionView(value=value, label=str(value))
            for value in range(config.minimum, config.maximum + 1)
        )
        kind = DayPromptKind.CHOICES
    elif isinstance(config, OrdinalConfig):
        options = tuple(
            DayValueOptionView(value=option.value, label=option.label)
            for option in config.options
        )
        kind = DayPromptKind.CHOICES
    else:
        options = ()
        kind = DayPromptKind.TEXT
    return DayValuePromptView(
        card=make_day_card_view(form),
        field_id=field.id,
        field_name=field.name,
        kind=kind,
        options=options,
    )


@dataclass(frozen=True, slots=True)
class ReferenceReviewView:
    """Display data for a best/worst personal-reference question."""

    day_id: UUID
    type: ReferenceType


def make_reference_review_view(review: ReferenceReview) -> ReferenceReviewView:
    """Map an application reference decision into presentation data."""
    return ReferenceReviewView(day_id=review.day_id, type=review.type)


@dataclass
class ReferenceReviewScreen(Screen):
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 4

    view: ReferenceReviewView

    @override
    def _text(self) -> ScreenContent:
        adjective = "лучше" if self.view.type.value == "best" else "хуже"
        return TEXTS[TextKey.REFERENCE_QUESTION].format(adjective=adjective)

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            *(
                (
                    label,
                    ReferenceCallback(
                        day_id=self.view.day_id,
                        type=self.view.type,
                        is_new_record=is_new_record,
                    ),
                )
                for is_new_record, label in (
                    (True, TEXTS[TextKey.YES]),
                    (False, TEXTS[TextKey.NO]),
                )
            )
        ).row((TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME)))
        return self._kbuilder.as_markup()

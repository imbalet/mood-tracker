"""UI-ready data for the interactive daily-entry screens."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

from mood_tracker.application.commands import DayForm, ReferenceReview
from mood_tracker.domain.entities import Event, Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import DayStatus, ReferenceType


class DayFieldAction(StrEnum):
    """One action a user may take from the day summary."""

    ADD = "add"
    EDIT = "edit"


class DayPromptKind(StrEnum):
    """Input control appropriate for a selected field."""

    CHOICES = "choices"
    TEXT = "text"


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
class DayCardView:
    """All display-ready data for one daily entry summary."""

    day: str
    date_label: str
    is_complete: bool
    entries: tuple[DayEntryView, ...]
    actions: tuple[DayFieldActionView, ...]
    events: tuple[DayEventView, ...] = ()


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


@dataclass(frozen=True, slots=True)
class ReferenceReviewView:
    """Display data for a best/worst personal-reference question."""

    day_id: UUID
    type: ReferenceType


def make_day_card_view(form: DayForm, events: tuple[Event, ...] = ()) -> DayCardView:
    """Map a day aggregate into the values needed by its Telegram card."""
    entries = tuple(_entry_views(form))
    actions = tuple(_action_views(form))
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


def make_reference_review_view(review: ReferenceReview) -> ReferenceReviewView:
    """Map an application reference decision into presentation data."""
    return ReferenceReviewView(day_id=review.day_id, type=review.type)


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
                rendered_value=_render_value(value.value, version.config),
                emoji=field.display_config.emoji,
                is_skipped=False,
            )
        )
    return entries


def _action_views(form: DayForm) -> list[DayFieldActionView]:
    actions: list[DayFieldActionView] = []
    for field in form.fields:
        placement = form.placements.get(field.id)
        if placement is None:
            continue
        is_completed = form.day is not None and form.day.has_completed_step(field.id)
        if is_completed:
            action = DayFieldAction.EDIT
        elif placement.is_enabled:
            action = DayFieldAction.ADD
        else:
            continue
        actions.append(DayFieldActionView(field.id, field.name, action))
    return actions


def _render_value(value: int | str, config: object) -> str:
    if isinstance(config, OrdinalConfig) and isinstance(value, int):
        return next(
            (option.label for option in config.options if option.value == value),
            str(value),
        )
    if isinstance(config, ScaleConfig):
        return f"{value}/{config.maximum}"
    return str(value)

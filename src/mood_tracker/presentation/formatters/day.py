"""Formatting of diary aggregates for Telegram messages."""

from html import escape

from mood_tracker.application.commands import DayForm
from mood_tracker.domain.entities import OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import FieldStatus
from mood_tracker.presentation.constants import TEXTS, TextKey


def format_day_card(form: DayForm) -> str:
    """Render visible persisted values with their historical field versions."""
    if form.day is None:
        return TEXTS[TextKey.EMPTY_DAY]
    lines = [f"<b>{form.day_date:%d.%m.%Y}</b>"]
    for field in form.fields:
        if field.status is FieldStatus.HIDDEN:
            continue
        value = form.day.values.get(field.id)
        if value is None:
            continue
        version = field.get_version(value.field_version_id)
        if version is None:
            continue
        rendered = str(value.value)
        if isinstance(version.config, OrdinalConfig) and isinstance(value.value, int):
            rendered = next(
                (
                    option.label
                    for option in version.config.options
                    if option.value == value.value
                ),
                rendered,
            )
        elif isinstance(version.config, ScaleConfig):
            rendered = f"{value.value}/{version.config.maximum}"
        emoji = f"{field.display_config.emoji} " if field.display_config.emoji else ""
        lines.append(f"{emoji}<b>{escape(field.name)}</b>: {escape(rendered)}")
    return "\n".join(lines)

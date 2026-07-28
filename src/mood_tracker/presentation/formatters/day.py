"""Formatting of diary aggregates for Telegram messages."""

from html import escape

from mood_tracker.application.commands import DayForm
from mood_tracker.domain.entities import OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import DayStatus, FieldStatus
from mood_tracker.presentation.constants import TEXTS, TextKey


def format_day_card(form: DayForm, prompt: str | None = None) -> str:
    """Render visible persisted values with their historical field versions."""
    status = (
        TextKey.DAY_COMPLETE
        if form.day is not None and form.day.status is DayStatus.COMPLETE
        else TextKey.DAY_DRAFT
    )
    lines = [f"<b>{form.day_date:%d.%m.%Y}</b> · {TEXTS[status]}"]
    if form.day is None:
        lines.append(TEXTS[TextKey.EMPTY_DAY])
        if prompt is not None:
            lines.append(prompt)
        return "\n\n".join(lines)
    has_progress = False
    for field in form.fields:
        if field.status is FieldStatus.HIDDEN:
            continue
        value = form.day.values.get(field.id)
        progress = form.day.progress.get(field.id)
        if value is None and progress is None:
            continue
        has_progress = True
        emoji = f"{field.display_config.emoji} " if field.display_config.emoji else ""
        if value is None:
            lines.append(
                f"{emoji}<b>{escape(field.name)}</b>: {TEXTS[TextKey.DAY_SKIPPED]}"
            )
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
        lines.append(f"{emoji}<b>{escape(field.name)}</b>: {escape(rendered)}")
    if not has_progress:
        lines.append(TEXTS[TextKey.EMPTY_DAY])
    if prompt is not None:
        lines.append(prompt)
    return "\n\n".join(lines)

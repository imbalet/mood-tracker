"""Telegram formatting for configurable diary fields."""

from html import escape

from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.enums import FieldStatus, FieldType
from mood_tracker.presentation.constants import TEXTS, TextKey


def format_fields_list(fields: tuple[Field, ...]) -> str:
    """Render a concise introduction above the field-selection keyboard."""
    if not fields:
        return "\n\n".join((TEXTS[TextKey.FIELDS_TITLE], TEXTS[TextKey.NO_FIELDS]))
    return TEXTS[TextKey.FIELDS_TITLE]


def format_field_card(field: Field) -> str:
    """Render current semantics and display configuration of one field."""
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        semantics = f"Шкала: <code>{config.minimum}–{config.maximum}</code>"
    elif isinstance(config, OrdinalConfig):
        semantics = "Варианты: " + ", ".join(
            f"<code>{escape(option.label)}</code>" for option in config.options
        )
    else:
        semantics = "Свободный текст"
    emoji = field.display_config.emoji or "—"
    calendar = "да" if field.display_config.show_in_calendar else "нет"
    status = _status_label(field.status)
    type_name = _type_label(field.current_version.type)
    lines = [
        TEXTS[TextKey.FIELD_DETAILS].format(name=escape(field.name)),
        f"Тип: {type_name}",
        f"Статус: <b>{status}</b>",
        semantics,
        f"Emoji: {escape(emoji)}",
        f"Показывать в календаре: {calendar}",
        f"Версий значений: {len(field.versions)}",
        TEXTS[TextKey.FIELD_POSITION].format(position=field.sort_order + 1),
    ]
    if field.display_config.state_palette is not None:
        palette = field.display_config.state_palette
        lines.append(
            "Палитра: "
            f"<code>{palette.minimum} → {palette.middle} → {palette.maximum}</code>"
        )
    return "\n".join(lines)


def _status_label(status: FieldStatus) -> str:
    return TEXTS[
        {
            FieldStatus.ACTIVE: TextKey.FIELD_STATUS_ACTIVE,
            FieldStatus.INACTIVE: TextKey.FIELD_STATUS_INACTIVE,
            FieldStatus.HIDDEN: TextKey.FIELD_STATUS_HIDDEN,
        }[status]
    ]


def _type_label(type: FieldType) -> str:
    return TEXTS[
        {
            FieldType.SCALE: TextKey.FIELD_TYPE_SCALE,
            FieldType.ORDINAL: TextKey.FIELD_TYPE_ORDINAL,
            FieldType.TEXT: TextKey.FIELD_TYPE_TEXT,
        }[type]
    ]

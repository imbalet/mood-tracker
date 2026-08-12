"""Shared conversions between JSONB payloads and domain value objects."""

from typing import Any

from mood_tracker.domain.entities import (
    FieldConfig,
    FieldDisplayConfig,
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
    StatePalette,
    TextConfig,
)
from mood_tracker.domain.enums import FieldType
from mood_tracker.infrastructure.db.models import FieldVersionOrm


def config_to_json(config: FieldConfig) -> dict[str, Any]:
    if isinstance(config, ScaleConfig):
        return {"min": config.minimum, "max": config.maximum}
    if isinstance(config, OrdinalConfig):
        return {
            "options": [{"value": o.value, "label": o.label} for o in config.options]
        }
    return {}


def config_from_json(type: FieldType, data: dict[str, Any]) -> FieldConfig:
    if type is FieldType.SCALE:
        return ScaleConfig(data["min"], data["max"])
    if type is FieldType.ORDINAL:
        return OrdinalConfig(
            tuple(OrdinalOption(o["value"], o["label"]) for o in data["options"])
        )
    return TextConfig()


def display_to_json(config: FieldDisplayConfig) -> dict[str, Any]:
    result: dict[str, Any] = {
        "emoji": config.emoji,
        "show_in_calendar": config.show_in_calendar,
    }
    if config.state_palette:
        result["state_palette"] = {
            "min": config.state_palette.minimum,
            "middle": config.state_palette.middle,
            "max": config.state_palette.maximum,
        }
    return result


def display_from_json(data: dict[str, Any]) -> FieldDisplayConfig:
    palette = data.get("state_palette")
    return FieldDisplayConfig(
        emoji=data.get("emoji"),
        show_in_calendar=data.get("show_in_calendar", True),
        state_palette=(
            StatePalette(palette["min"], palette["middle"], palette["max"])
            if palette
            else None
        ),
    )


def version_to_orm(version: FieldVersion) -> FieldVersionOrm:
    return FieldVersionOrm(
        id=version.id,
        field_id=version.field_id,
        type=version.type.value,
        config=config_to_json(version.config),
        created_at=version.created_at,
    )


def version_from_orm(row: FieldVersionOrm) -> FieldVersion:
    type = FieldType(row.type)
    return FieldVersion(
        row.id, row.field_id, config_from_json(type, row.config), row.created_at
    )

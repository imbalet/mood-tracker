"""Factories for the four standard fields of a newly registered user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities import (
    EventFieldConfig,
    Field,
    FieldDisplayConfig,
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
    StatePalette,
    TextConfig,
)
from mood_tracker.domain.enums import FieldStatus, FieldType


@dataclass(frozen=True, slots=True)
class DefaultFieldIds:
    """IDs supplied by application for the four default fields and versions."""

    state_field: UUID
    state_version: UUID
    crying_field: UUID
    crying_version: UUID
    thoughts_field: UUID
    thoughts_version: UUID
    comment_field: UUID
    comment_version: UUID
    event_description_field: UUID
    event_description_version: UUID


def create_default_fields(
    user_id: UUID, ids: DefaultFieldIds, created_at: datetime
) -> tuple[Field, Field, Field, Field, Field]:
    """Create the standard active fields in their questionnaire display order."""
    state_version = FieldVersion(
        id=ids.state_version,
        field_id=ids.state_field,
        type=FieldType.SCALE,
        config=ScaleConfig(minimum=0, maximum=10),
        created_at=created_at,
    )
    crying_version = FieldVersion(
        id=ids.crying_version,
        field_id=ids.crying_field,
        type=FieldType.ORDINAL,
        config=OrdinalConfig(
            options=(
                OrdinalOption(0, "Нет"),
                OrdinalOption(1, "Немного"),
                OrdinalOption(2, "Был"),
                OrdinalOption(3, "Сильно"),
            )
        ),
        created_at=created_at,
    )
    thoughts_version = FieldVersion(
        id=ids.thoughts_version,
        field_id=ids.thoughts_field,
        type=FieldType.ORDINAL,
        config=OrdinalConfig(
            options=(
                OrdinalOption(0, "Нет"),
                OrdinalOption(1, "Были"),
                OrdinalOption(2, "Много"),
                OrdinalOption(3, "Очень много"),
            )
        ),
        created_at=created_at,
    )
    comment_version = FieldVersion(
        id=ids.comment_version,
        field_id=ids.comment_field,
        type=FieldType.TEXT,
        config=TextConfig(),
        created_at=created_at,
    )
    event_description_version = FieldVersion(
        id=ids.event_description_version,
        field_id=ids.event_description_field,
        type=FieldType.TEXT,
        config=TextConfig(),
        created_at=created_at,
    )
    return (
        Field(
            id=ids.state_field,
            user_id=user_id,
            name="Состояние",
            status=FieldStatus.ACTIVE,
            is_core=True,
            sort_order=0,
            display_config=FieldDisplayConfig(
                state_palette=StatePalette("#D96C75", "#B8BEC7", "#6FAF8F")
            ),
            current_version=state_version,
        ),
        Field(
            id=ids.crying_field,
            user_id=user_id,
            name="Плач",
            status=FieldStatus.ACTIVE,
            is_core=False,
            sort_order=1,
            display_config=FieldDisplayConfig(emoji="💧"),
            current_version=crying_version,
        ),
        Field(
            id=ids.thoughts_field,
            user_id=user_id,
            name="Негативные мысли",
            status=FieldStatus.ACTIVE,
            is_core=False,
            sort_order=2,
            display_config=FieldDisplayConfig(emoji="💀"),
            current_version=thoughts_version,
        ),
        Field(
            id=ids.comment_field,
            user_id=user_id,
            name="Комментарий",
            status=FieldStatus.ACTIVE,
            is_core=False,
            sort_order=3,
            display_config=FieldDisplayConfig(),
            current_version=comment_version,
        ),
        Field(
            id=ids.event_description_field,
            user_id=user_id,
            name="Описание",
            status=FieldStatus.ACTIVE,
            is_core=False,
            sort_order=4,
            display_config=FieldDisplayConfig(),
            current_version=event_description_version,
            event_config=EventFieldConfig(required=False, sort_order=0, is_system=True),
        ),
    )

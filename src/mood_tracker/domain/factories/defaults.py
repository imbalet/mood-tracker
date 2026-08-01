"""Factories for the standard day and event fields of a new user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities import (
    Field,
    FieldDisplayConfig,
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
    Questionnaire,
    ScaleConfig,
    StatePalette,
    TextConfig,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    FieldType,
    QuestionnaireFieldRole,
    QuestionnaireKind,
)


@dataclass(frozen=True, slots=True)
class DefaultFieldIds:
    state_field: UUID
    state_version: UUID
    thoughts_field: UUID
    thoughts_version: UUID
    comment_field: UUID
    comment_version: UUID
    event_description_field: UUID
    event_description_version: UUID


def create_default_fields(
    user_id: UUID, ids: DefaultFieldIds, created_at: datetime
) -> tuple[Field, Field, Field, Field]:
    """Create the two independent default questionnaires' reusable fields."""

    def version(
        field_id: UUID, version_id: UUID, type: FieldType, config: object
    ) -> FieldVersion:
        return FieldVersion(version_id, field_id, type, config, created_at)  # type: ignore[arg-type]

    state = version(
        ids.state_field, ids.state_version, FieldType.SCALE, ScaleConfig(0, 10)
    )
    thoughts = version(
        ids.thoughts_field,
        ids.thoughts_version,
        FieldType.ORDINAL,
        OrdinalConfig(
            (
                OrdinalOption(0, "Нет"),
                OrdinalOption(1, "Были"),
                OrdinalOption(2, "Много"),
                OrdinalOption(3, "Очень много"),
            )
        ),
    )
    comment = version(
        ids.comment_field, ids.comment_version, FieldType.TEXT, TextConfig()
    )
    description = version(
        ids.event_description_field,
        ids.event_description_version,
        FieldType.TEXT,
        TextConfig(),
    )
    return (
        Field(
            ids.state_field,
            user_id,
            "Состояние",
            FieldDisplayConfig(
                state_palette=StatePalette("#D96C75", "#B8BEC7", "#6FAF8F")
            ),
            state,
        ),
        Field(
            ids.thoughts_field,
            user_id,
            "Негативные мысли",
            FieldDisplayConfig(emoji="💀"),
            thoughts,
        ),
        Field(
            ids.comment_field,
            user_id,
            "Комментарий",
            FieldDisplayConfig(),
            comment,
        ),
        Field(
            ids.event_description_field,
            user_id,
            "Описание",
            FieldDisplayConfig(),
            description,
        ),
    )


def create_default_questionnaires(
    user_id: UUID, day_id: UUID, event_id: UUID, field_ids: DefaultFieldIds
) -> tuple[Questionnaire, Questionnaire]:
    """Create the independent placement aggregates for standard fields."""
    return (
        Questionnaire(
            day_id,
            user_id,
            QuestionnaireKind.DAY,
            {
                field_ids.state_field: QuestionnaireField(
                    field_ids.state_field, 0, role=QuestionnaireFieldRole.DAY_STATE
                ),
                field_ids.thoughts_field: QuestionnaireField(
                    field_ids.thoughts_field, 1
                ),
                field_ids.comment_field: QuestionnaireField(
                    field_ids.comment_field, 2, is_required=False
                ),
            },
        ),
        Questionnaire(
            event_id,
            user_id,
            QuestionnaireKind.EVENT,
            {
                field_ids.event_description_field: QuestionnaireField(
                    field_ids.event_description_field,
                    0,
                    is_required=False,
                    role=QuestionnaireFieldRole.EVENT_DESCRIPTION,
                )
            },
        ),
    )

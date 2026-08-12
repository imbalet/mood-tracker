"""Factories for the standard day and event fields of a new user."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID

from mood_tracker.domain.entities import (
    Field,
    FieldConfig,
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
    QuestionnaireFieldRole,
    QuestionnaireKind,
)


@dataclass(frozen=True, slots=True)
class DefaultProfileSetup:
    fields: tuple[Field, ...]
    questionnaires: tuple[Questionnaire, ...]


@dataclass(frozen=True, slots=True)
class DefaultProfileIds:
    # fields
    state_field: UUID
    state_version: UUID
    thoughts_field: UUID
    thoughts_version: UUID
    comment_field: UUID
    comment_version: UUID
    event_description_field: UUID
    event_description_version: UUID

    # questionnaires
    day_questionnaire: UUID
    event_questionnaire: UUID

    @classmethod
    def generate(cls, new_id: Callable[[], UUID]) -> Self:
        return cls(
            state_field=new_id(),
            state_version=new_id(),
            thoughts_field=new_id(),
            thoughts_version=new_id(),
            comment_field=new_id(),
            comment_version=new_id(),
            event_description_field=new_id(),
            event_description_version=new_id(),
            day_questionnaire=new_id(),
            event_questionnaire=new_id(),
        )


def create_default_profile_setup(
    user_id: UUID,
    ids: DefaultProfileIds,
    created_at: datetime,
) -> DefaultProfileSetup:
    return DefaultProfileSetup(
        fields=_create_default_fields(user_id=user_id, ids=ids, created_at=created_at),
        questionnaires=_create_default_questionnaires(user_id=user_id, ids=ids),
    )


def _create_default_fields(
    user_id: UUID, ids: DefaultProfileIds, created_at: datetime
) -> tuple[Field, Field, Field, Field]:
    """Create the two independent default questionnaires' reusable fields."""

    def version(field_id: UUID, version_id: UUID, config: FieldConfig) -> FieldVersion:
        return FieldVersion(version_id, field_id, config, created_at)

    state = version(ids.state_field, ids.state_version, ScaleConfig(0, 10))
    thoughts = version(
        ids.thoughts_field,
        ids.thoughts_version,
        OrdinalConfig(
            (
                OrdinalOption(0, "Нет"),
                OrdinalOption(1, "Были"),
                OrdinalOption(2, "Много"),
                OrdinalOption(3, "Очень много"),
            )
        ),
    )
    comment = version(ids.comment_field, ids.comment_version, TextConfig())
    description = version(
        ids.event_description_field,
        ids.event_description_version,
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


def _create_default_questionnaires(
    user_id: UUID, ids: DefaultProfileIds
) -> tuple[Questionnaire, Questionnaire]:
    """Create the independent placement aggregates for standard fields."""
    return (
        Questionnaire(
            ids.day_questionnaire,
            user_id,
            QuestionnaireKind.DAY,
            {
                ids.state_field: QuestionnaireField(
                    ids.state_field, 0, role=QuestionnaireFieldRole.DAY_STATE
                ),
                ids.thoughts_field: QuestionnaireField(ids.thoughts_field, 1),
                ids.comment_field: QuestionnaireField(
                    ids.comment_field, 2, is_required=False
                ),
            },
        ),
        Questionnaire(
            ids.event_questionnaire,
            user_id,
            QuestionnaireKind.EVENT,
            {
                ids.event_description_field: QuestionnaireField(
                    ids.event_description_field,
                    0,
                    is_required=False,
                    role=QuestionnaireFieldRole.EVENT_DESCRIPTION,
                )
            },
        ),
    )

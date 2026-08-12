"""Questionnaire and field-management application contracts."""

from dataclasses import dataclass
from uuid import UUID

from mood_tracker.domain.entities import Field, FieldConfig, FieldDisplayConfig
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import MoveDirection, QuestionnaireKind


@dataclass(frozen=True, slots=True)
class CreateField:
    """Create one custom field and its initial semantic version."""

    user_id: UUID
    name: str
    config: FieldConfig
    display_config: FieldDisplayConfig
    kind: QuestionnaireKind = QuestionnaireKind.DAY


@dataclass(frozen=True, slots=True)
class RenameField:
    """Rename one user-owned field."""

    user_id: UUID
    field_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class SetFieldDisplay:
    """Replace one field's current display configuration."""

    user_id: UUID
    field_id: UUID
    display_config: FieldDisplayConfig


@dataclass(frozen=True, slots=True)
class AddFieldVersion:
    """Append a new semantic configuration to one field."""

    user_id: UUID
    field_id: UUID
    config: FieldConfig


@dataclass(frozen=True, slots=True)
class ListQuestionnaireFields:
    """Read fields assigned to one explicit questionnaire."""

    user_id: UUID
    kind: QuestionnaireKind


@dataclass(frozen=True, slots=True)
class QuestionnaireFieldItem:
    """A semantic field resolved with its placement in one questionnaire."""

    field: Field
    placement: QuestionnaireField


@dataclass(frozen=True, slots=True)
class AttachFieldToQuestionnaire:
    """Attach an existing semantic field to one questionnaire."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    is_required: bool = False


@dataclass(frozen=True, slots=True)
class DetachFieldFromQuestionnaire:
    """Remove a non-system field from one questionnaire only."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind


@dataclass(frozen=True, slots=True)
class SetQuestionnaireFieldEnabled:
    """Hide or restore a field without deleting its historical values."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    is_enabled: bool


@dataclass(frozen=True, slots=True)
class SetQuestionnaireFieldRequired:
    """Change whether a questionnaire step may be skipped."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    is_required: bool


@dataclass(frozen=True, slots=True)
class MoveQuestionnaireField:
    """Move a field inside one explicit questionnaire."""

    user_id: UUID
    field_id: UUID
    kind: QuestionnaireKind
    direction: MoveDirection


@dataclass(frozen=True, slots=True)
class DeleteField:
    """Soft-delete a semantic field globally."""

    user_id: UUID
    field_id: UUID

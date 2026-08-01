"""User questionnaires and their independent field placements."""

from dataclasses import dataclass, field
from uuid import UUID

from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.errors import CoreFieldViolation, InvalidFieldVersion


@dataclass(slots=True)
class QuestionnaireField:
    """One field's order and requirements within a single questionnaire."""

    field_id: UUID
    sort_order: int
    is_enabled: bool = True
    is_required: bool = True
    role: QuestionnaireFieldRole = QuestionnaireFieldRole.ORDINARY

    def __post_init__(self) -> None:
        if self.sort_order < 0:
            msg = "Questionnaire field sort order cannot be negative"
            raise InvalidFieldVersion(msg)
        if self.role is QuestionnaireFieldRole.DAY_STATE and (
            not self.is_enabled or not self.is_required
        ):
            msg = "Day state field must remain enabled and required"
            raise CoreFieldViolation(msg)

    def set_enabled(self, is_enabled: bool) -> None:
        """Toggle question visibility while protecting the daily-state invariant."""
        if self.role is QuestionnaireFieldRole.DAY_STATE and not is_enabled:
            msg = "Day state field must remain enabled"
            raise CoreFieldViolation(msg)
        self.is_enabled = is_enabled


@dataclass(slots=True)
class Questionnaire:
    """One built-in user questionnaire and its field placements."""

    id: UUID
    user_id: UUID
    kind: QuestionnaireKind
    fields: dict[UUID, QuestionnaireField] = field(default_factory=dict)

    def ordered_fields(self) -> tuple[QuestionnaireField, ...]:
        return tuple(sorted(self.fields.values(), key=lambda item: item.sort_order))

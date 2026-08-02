"""User questionnaires and their independent field placements."""

from dataclasses import dataclass, field
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
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
        if (
            self.role is QuestionnaireFieldRole.EVENT_DESCRIPTION
            and not self.is_enabled
        ):
            msg = "Event description field must remain enabled"
            raise CoreFieldViolation(msg)

    def set_enabled(self, is_enabled: bool) -> None:
        """Toggle question visibility while protecting the daily-state invariant."""
        if (
            self.role
            in (
                QuestionnaireFieldRole.DAY_STATE,
                QuestionnaireFieldRole.EVENT_DESCRIPTION,
            )
            and not is_enabled
        ):
            msg = "System questionnaire field must remain enabled"
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


@dataclass(frozen=True, slots=True)
class Answer:
    """A concrete value saved with the semantic field version that defined it."""

    field_id: UUID
    field_version_id: UUID
    value: int | str
    normalized_value: float | None

    @classmethod
    def from_input(cls, field_version: FieldVersion, value: int | str) -> Answer:
        """Validate user input against a version and construct a stored value."""
        normalized_value = field_version.validate_value(value)
        return cls(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            value=value,
            normalized_value=normalized_value,
        )


@dataclass(frozen=True, slots=True)
class QuestionProgress:
    """A persisted fact that the user answered or skipped one field step."""

    field_id: UUID
    field_version_id: UUID
    skipped: bool


@dataclass(slots=True)
class QuestionnaireResponse:
    answers: dict[UUID, Answer] = field(default_factory=dict)
    progress: dict[UUID, QuestionProgress] = field(default_factory=dict)

    def answer(self, field_version: FieldVersion, value: int | str) -> Answer:
        """Save or replace a value and mark its field step as completed."""
        answer = Answer.from_input(field_version, value)
        self.answers[field_version.field_id] = answer
        self.progress[field_version.field_id] = QuestionProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=False,
        )
        return answer

    def skip(self, field_version: FieldVersion) -> None:
        """Mark a questionnaire field as deliberately skipped."""
        self.answers.pop(field_version.field_id, None)
        self.progress[field_version.field_id] = QuestionProgress(
            field_id=field_version.field_id,
            field_version_id=field_version.id,
            skipped=True,
        )

    def has_completed_step(self, field_id: UUID) -> bool:
        """Whether the questionnaire step has been answered or explicitly skipped."""
        return field_id in self.progress

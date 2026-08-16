"""User questionnaires and their independent field placements."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from mood_tracker.domain.entities.field import FieldVersion
from mood_tracker.domain.enums import (
    MoveDirection,
    QuestionnaireFieldRole,
    QuestionnaireKind,
)
from mood_tracker.domain.errors import (
    CoreFieldViolation,
    InvalidFieldVersion,
    QuestionnaireViolation,
)
from mood_tracker.domain.value_objects import require_utc


@dataclass(slots=True)
class QuestionnaireField:
    """One field's order and requirements within a single questionnaire."""

    field_id: UUID
    sort_order: int
    is_enabled: bool = True
    is_required: bool = True
    role: QuestionnaireFieldRole = QuestionnaireFieldRole.ORDINARY
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.deleted_at is not None:
            self.deleted_at = require_utc(
                self.deleted_at, "Questionnaire field deletion time"
            )
        if self.sort_order < 0:
            msg = "Questionnaire field sort order cannot be negative"
            raise InvalidFieldVersion(msg)
        # TODO: maybe refactor
        if self.role is QuestionnaireFieldRole.DAY_STATE and (
            not self.is_enabled or not self.is_required or self.deleted_at is not None
        ):
            msg = "Day state field must remain enabled and required"
            raise CoreFieldViolation(msg)
        if self.role is QuestionnaireFieldRole.EVENT_DESCRIPTION and (
            not self.is_enabled or self.deleted_at is not None
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

    def delete(self, deleted_at: datetime) -> None:
        """Hide an ordinary placement while preserving its history and order."""
        if self.role is not QuestionnaireFieldRole.ORDINARY:
            msg = "System questionnaire field cannot be deleted"
            raise CoreFieldViolation(msg)
        self.deleted_at = require_utc(deleted_at, "Questionnaire field deletion time")

    def restore(self) -> None:
        """Restore a previously removed placement as an enabled question."""
        if self.deleted_at is None:
            msg = "Questionnaire field is not deleted"
            raise QuestionnaireViolation(msg)
        self.deleted_at = None
        self.is_enabled = True

    def set_required(self, is_required: bool) -> None:
        """Change whether a questionnaire step must be completed."""
        if self.role is QuestionnaireFieldRole.DAY_STATE and not is_required:
            msg = "Day state field must remain required"
            raise CoreFieldViolation(msg)
        self.is_required = is_required


@dataclass(slots=True)
class Questionnaire:
    """One built-in user questionnaire and its field placements."""

    id: UUID
    user_id: UUID
    kind: QuestionnaireKind
    fields: dict[UUID, QuestionnaireField] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_id, placement in self.fields.items():
            if field_id != placement.field_id:
                msg = "Questionnaire field key must match placement field ID"
                raise QuestionnaireViolation(msg)
            self._validate_role(placement.role)
        sort_orders = sorted(placement.sort_order for placement in self.fields.values())
        if sort_orders != list(range(len(self.fields))):
            msg = "Questionnaire field order must be contiguous and unique"
            raise QuestionnaireViolation(msg)

    def ordered_fields(self) -> tuple[QuestionnaireField, ...]:
        return tuple(sorted(self.fields.values(), key=lambda item: item.sort_order))

    def enabled_field_ids(self) -> tuple[UUID, ...]:
        """Return enabled field IDs in questionnaire order."""
        return tuple(
            placement.field_id
            for placement in self.ordered_fields()
            if placement.is_enabled and placement.deleted_at is None
        )

    def required_enabled_field_ids(self) -> tuple[UUID, ...]:
        """Return enabled required field IDs in questionnaire order."""
        return tuple(
            placement.field_id
            for placement in self.ordered_fields()
            if (
                placement.is_enabled
                and placement.deleted_at is None
                and placement.is_required
            )
        )

    def system_field_id(self, role: QuestionnaireFieldRole) -> UUID:
        """Return the single field ID assigned to a non-ordinary system role."""
        if role is QuestionnaireFieldRole.ORDINARY:
            msg = "Ordinary fields do not have a single system placement"
            raise QuestionnaireViolation(msg)
        field_ids = tuple(
            placement.field_id
            for placement in self.fields.values()
            if placement.role is role
        )
        if len(field_ids) != 1:
            msg = f"Questionnaire must have exactly one {role} field"
            raise QuestionnaireViolation(msg)
        return field_ids[0]

    def attach(
        self,
        field_id: UUID,
        *,
        is_required: bool = False,
        role: QuestionnaireFieldRole = QuestionnaireFieldRole.ORDINARY,
    ) -> QuestionnaireField:
        """Append a new field placement to this questionnaire."""
        existing = self.fields.get(field_id)
        if existing is not None:
            if existing.deleted_at is not None:
                existing.restore()
                return existing
            msg = "Field is already attached to this questionnaire"
            raise QuestionnaireViolation(msg)
        self._validate_role(role)
        placement = QuestionnaireField(
            field_id=field_id,
            sort_order=len(self.fields),
            is_required=is_required,
            role=role,
        )
        self.fields[field_id] = placement
        return placement

    def delete(self, field_id: UUID, deleted_at: datetime) -> QuestionnaireField:
        """Soft-delete one ordinary placement without changing its absolute order."""
        placement = self._placement(field_id)
        placement.delete(deleted_at)
        return placement

    def set_enabled(self, field_id: UUID, is_enabled: bool) -> None:
        """Change one placement's visibility in this questionnaire."""
        self._placement(field_id).set_enabled(is_enabled)

    def set_required(self, field_id: UUID, is_required: bool) -> None:
        """Change one placement's completion requirement."""
        self._placement(field_id).set_required(is_required)

    def move(self, field_id: UUID, direction: MoveDirection) -> None:
        """Move a placement by one position without creating order gaps."""
        placements = [
            placement
            for placement in self.ordered_fields()
            if placement.deleted_at is None
        ]
        current_index = next(
            (
                index
                for index, placement in enumerate(placements)
                if placement.field_id == field_id
            ),
            None,
        )
        if current_index is None:
            msg = "Field is not attached to this questionnaire"
            raise QuestionnaireViolation(msg)
        target_index = current_index + (-1 if direction is MoveDirection.UP else 1)
        if 0 <= target_index < len(placements):
            placements[current_index], placements[target_index] = (
                placements[target_index],
                placements[current_index],
            )
            original_orders = sorted(placement.sort_order for placement in placements)
            for placement, sort_order in zip(placements, original_orders, strict=True):
                placement.sort_order = sort_order

    def _placement(self, field_id: UUID) -> QuestionnaireField:
        placement = self.fields.get(field_id)
        if placement is None:
            msg = "Field is not attached to this questionnaire"
            raise QuestionnaireViolation(msg)
        return placement

    def _validate_role(self, role: QuestionnaireFieldRole) -> None:
        if (
            role is QuestionnaireFieldRole.DAY_STATE
            and self.kind is not QuestionnaireKind.DAY
        ):
            msg = "Day state field can only belong to a day questionnaire"
            raise QuestionnaireViolation(msg)
        if (
            role is QuestionnaireFieldRole.EVENT_DESCRIPTION
            and self.kind is not QuestionnaireKind.EVENT
        ):
            msg = "Event description field can only belong to an event questionnaire"
            raise QuestionnaireViolation(msg)


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

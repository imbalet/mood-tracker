"""Field aggregates, immutable semantic versions and display configuration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, override
from uuid import UUID

from mood_tracker.domain.enums import FieldType
from mood_tracker.domain.errors import (
    InvalidFieldValue,
    InvalidFieldVersion,
)
from mood_tracker.domain.value_objects import require_utc


def _require_non_empty(value: str, label: str) -> None:
    if not value.strip():
        msg = f"{label} cannot be empty"
        raise InvalidFieldVersion(msg)


def _require_hex_color(value: str) -> None:
    if len(value) != 7 or not value.startswith("#"):
        msg = "Color must use the #RRGGBB format"
        raise InvalidFieldVersion(msg)
    try:
        int(value[1:], 16)
    except ValueError as error:
        msg = "Color must use the #RRGGBB format"
        raise InvalidFieldVersion(msg) from error


class FieldConfig(ABC):
    """Abstract semantic contract implemented by every field configuration."""

    field_type: ClassVar[FieldType]

    @abstractmethod
    def validate_value(self, value: int | str) -> float | None:
        """Validate raw input and return its normalized value when applicable."""


@dataclass(frozen=True, slots=True)
class ScaleConfig(FieldConfig):
    """Inclusive integer range for a scale field version."""

    field_type: ClassVar[FieldType] = FieldType.SCALE
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if isinstance(self.minimum, bool) or isinstance(self.maximum, bool):
            msg = "Scale boundaries must be integers"
            raise InvalidFieldVersion(msg)
        if self.minimum >= self.maximum:
            msg = "Scale minimum must be smaller than maximum"
            raise InvalidFieldVersion(msg)

    def normalize(self, value: int) -> float:
        """Return a scale value normalized to the inclusive 0..1 range."""
        if isinstance(value, bool) or not self.minimum <= value <= self.maximum:
            msg = "Scale value is outside the configured range"
            raise InvalidFieldVersion(msg)
        return (value - self.minimum) / (self.maximum - self.minimum)

    @override
    def validate_value(self, value: int | str) -> float:
        """Validate raw input and return its normalized scale value."""
        if not isinstance(value, int) or isinstance(value, bool):
            msg = "Scale value must be an integer"
            raise InvalidFieldValue(msg)
        try:
            return self.normalize(value)
        except InvalidFieldVersion as error:
            raise InvalidFieldValue(str(error)) from error


@dataclass(frozen=True, slots=True)
class OrdinalOption:
    """One ordered visible option of an ordinal field version."""

    value: int
    label: str

    def __post_init__(self) -> None:
        if isinstance(self.value, bool):
            msg = "Ordinal option value must be an integer"
            raise InvalidFieldVersion(msg)
        _require_non_empty(self.label, "Ordinal option label")


@dataclass(frozen=True, slots=True)
class OrdinalConfig(FieldConfig):
    """Sequential ordered options; a scale may start with any integer."""

    field_type: ClassVar[FieldType] = FieldType.ORDINAL
    options: tuple[OrdinalOption, ...]

    def __post_init__(self) -> None:
        if len(self.options) < 2:
            msg = "Ordinal fields need at least two options"
            raise InvalidFieldVersion(msg)
        values = tuple(option.value for option in self.options)
        expected = tuple(range(values[0], values[0] + len(values)))
        if values != expected:
            msg = "Ordinal option values must be sequential and ordered"
            raise InvalidFieldVersion(msg)

    @property
    def minimum(self) -> int:
        """Return the first configured ordinal value."""
        return self.options[0].value

    @property
    def maximum(self) -> int:
        """Return the last configured ordinal value."""
        return self.options[-1].value

    def normalize(self, value: int) -> float:
        """Return an ordinal value normalized to the inclusive 0..1 range."""
        if isinstance(value, bool) or not self.minimum <= value <= self.maximum:
            msg = "Ordinal value is not in the configured options"
            raise InvalidFieldVersion(msg)
        return (value - self.minimum) / (self.maximum - self.minimum)

    @override
    def validate_value(self, value: int | str) -> float:
        """Validate raw input and return its normalized ordinal value."""
        if not isinstance(value, int) or isinstance(value, bool):
            msg = "Ordinal value must be an integer"
            raise InvalidFieldValue(msg)
        try:
            return self.normalize(value)
        except InvalidFieldVersion as error:
            raise InvalidFieldValue(str(error)) from error


@dataclass(frozen=True, slots=True)
class TextConfig(FieldConfig):
    """Configuration marker for a free-text field version."""

    field_type: ClassVar[FieldType] = FieldType.TEXT

    @override
    def validate_value(self, value: int | str) -> None:
        """Validate non-empty text input with no numeric normalization."""
        if not isinstance(value, str) or not value.strip():
            msg = "Text value must be non-empty"
            raise InvalidFieldValue(msg)


@dataclass(frozen=True, slots=True)
class StatePalette:
    """Three-point palette used to color the core state field."""

    minimum: str
    middle: str
    maximum: str

    def __post_init__(self) -> None:
        _require_hex_color(self.minimum)
        _require_hex_color(self.middle)
        _require_hex_color(self.maximum)


@dataclass(frozen=True, slots=True)
class FieldDisplayConfig:
    """Current visual identity without prescribing a rendering algorithm."""

    emoji: str | None = None
    show_in_calendar: bool = True
    state_palette: StatePalette | None = None

    def __post_init__(self) -> None:
        if self.emoji is not None:
            _require_non_empty(self.emoji, "Field emoji")


@dataclass(frozen=True, slots=True)
class FieldVersion:
    """Immutable meaning of a field at the point a value is saved."""

    id: UUID
    field_id: UUID
    type: FieldType
    config: FieldConfig
    created_at: datetime

    def __post_init__(self) -> None:
        if self.type is not self.config.field_type:
            msg = f"{self.type} field version has incompatible config type"
            raise InvalidFieldVersion(msg)
        require_utc(self.created_at, "Field version creation time")

    def validate_value(self, value: int | str) -> float | None:
        """Validate raw input using this version's immutable field semantics."""
        return self.config.validate_value(value)


@dataclass(slots=True)
class Field:
    """A user-owned field with mutable presentation and current version pointer."""

    id: UUID
    user_id: UUID
    name: str
    display_config: FieldDisplayConfig
    current_version: FieldVersion
    versions: list[FieldVersion] = field(default_factory=list)
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "Field name")
        if self.current_version.field_id != self.id:
            msg = "Current field version belongs to another field"
            raise InvalidFieldVersion(msg)
        if not self.versions:
            self.versions.append(self.current_version)
        if self.current_version not in self.versions:
            msg = "Current field version must belong to field history"
            raise InvalidFieldVersion(msg)
        if self.deleted_at is not None:
            require_utc(self.deleted_at, "Field deletion time")

    @property
    def current_version_id(self) -> UUID:
        """Return the ID of the active semantic version."""
        return self.current_version.id

    def rename(self, name: str) -> None:
        """Change only the presentation name of the field."""
        _require_non_empty(name, "Field name")
        self.name = name

    def set_display_config(self, display_config: FieldDisplayConfig) -> None:
        """Replace current presentation without changing any semantic version."""
        self.display_config = display_config

    def delete(self, deleted_at: datetime) -> None:
        """Soft-delete this semantic field and all values that reference it."""
        self.deleted_at = require_utc(deleted_at, "Field deletion time")

    def add_version(self, version: FieldVersion) -> None:
        """Append a new immutable meaning and make it current."""
        if version.field_id != self.id:
            msg = "New field version belongs to another field"
            raise InvalidFieldVersion(msg)
        if any(existing.id == version.id for existing in self.versions):
            msg = "Field version ID already exists in this field"
            raise InvalidFieldVersion(msg)
        self.versions.append(version)
        self.current_version = version

    def get_version(self, version_id: UUID) -> FieldVersion | None:
        """Return one retained semantic version by its identifier."""
        return next(
            (version for version in self.versions if version.id == version_id), None
        )

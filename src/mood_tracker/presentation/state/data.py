"""Typed payloads persisted for short-lived presentation forms."""

from dataclasses import dataclass
from datetime import date
from typing import ClassVar, override
from uuid import UUID

from mood_tracker.domain.enums import FieldType


class FlowData:
    """Base protocol implemented by every serializable form payload."""

    kind: ClassVar[str]

    def to_payload(self) -> dict[str, object]:
        """Serialize the payload to FSM-storage primitives."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class CreateFieldNameData(FlowData):
    """The selected type while waiting for a new field name."""

    kind: ClassVar[str] = "create_field_name"
    field_type: FieldType

    @override
    def to_payload(self) -> dict[str, object]:
        return {"field_type": self.field_type.value}


@dataclass(frozen=True, slots=True)
class CreateFieldConfigData(FlowData):
    """The new field identity while collecting its semantic configuration."""

    kind: ClassVar[str] = "create_field_config"
    field_type: FieldType
    name: str

    @override
    def to_payload(self) -> dict[str, object]:
        return {"field_type": self.field_type.value, "name": self.name}


@dataclass(frozen=True, slots=True)
class RenameFieldData(FlowData):
    """The field being renamed."""

    kind: ClassVar[str] = "rename_field"
    field_id: UUID

    @override
    def to_payload(self) -> dict[str, object]:
        return {"field_id": str(self.field_id)}


@dataclass(frozen=True, slots=True)
class FieldVersionData(FlowData):
    """The field receiving a new semantic version."""

    kind: ClassVar[str] = "field_version"
    field_id: UUID

    @override
    def to_payload(self) -> dict[str, object]:
        return {"field_id": str(self.field_id)}


@dataclass(frozen=True, slots=True)
class CreateOrdinalData(FlowData):
    """Ordinal options being created for a new field."""

    kind: ClassVar[str] = "create_ordinal"
    name: str
    starts_at: int
    labels: tuple[str, ...]

    @override
    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "starts_at": self.starts_at,
            "labels": list(self.labels),
        }


@dataclass(frozen=True, slots=True)
class VersionOrdinalData(FlowData):
    """Ordinal options being created for an existing field version."""

    kind: ClassVar[str] = "version_ordinal"
    field_id: UUID
    starts_at: int
    labels: tuple[str, ...]

    @override
    def to_payload(self) -> dict[str, object]:
        return {
            "field_id": str(self.field_id),
            "starts_at": self.starts_at,
            "labels": list(self.labels),
        }


@dataclass(frozen=True, slots=True)
class FieldDisplayData(FlowData):
    """The field whose display-only configuration is being edited."""

    kind: ClassVar[str] = "field_display"
    field_id: UUID

    @override
    def to_payload(self) -> dict[str, object]:
        return {"field_id": str(self.field_id)}


@dataclass(frozen=True, slots=True)
class DiaryTextData(FlowData):
    """The pending Text answer for one owned diary day."""

    kind: ClassVar[str] = "diary_text"
    day_date: date
    field_id: UUID

    @override
    def to_payload(self) -> dict[str, object]:
        return {"day_date": self.day_date.isoformat(), "field_id": str(self.field_id)}

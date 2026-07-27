"""Builders for fields and their current semantic versions."""

from datetime import UTC, datetime
from uuid import UUID, uuid7

from mood_tracker.domain.entities import (
    Field,
    FieldConfig,
    FieldDisplayConfig,
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
    TextConfig,
)
from mood_tracker.domain.enums import FieldStatus, FieldType


class FieldFactory:
    """Build valid field aggregates for each supported semantic type."""

    def scale(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        version_id: UUID | None = None,
        name: str = "Состояние",
        minimum: int = 0,
        maximum: int = 10,
        status: FieldStatus = FieldStatus.ACTIVE,
        is_core: bool = False,
        sort_order: int = 0,
        display_config: FieldDisplayConfig | None = None,
        created_at: datetime = datetime(2025, 1, 2, tzinfo=UTC),
    ) -> Field:
        """Build a scale field."""
        return self._build(
            id=id,
            user_id=user_id,
            version_id=version_id,
            name=name,
            type=FieldType.SCALE,
            config=ScaleConfig(minimum, maximum),
            status=status,
            is_core=is_core,
            sort_order=sort_order,
            display_config=display_config,
            created_at=created_at,
        )

    def ordinal(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        version_id: UUID | None = None,
        name: str = "Показатель",
        options: tuple[OrdinalOption, ...] = (
            OrdinalOption(0, "Нет"),
            OrdinalOption(1, "Немного"),
            OrdinalOption(2, "Много"),
        ),
        status: FieldStatus = FieldStatus.ACTIVE,
        sort_order: int = 0,
        display_config: FieldDisplayConfig | None = None,
        created_at: datetime = datetime(2025, 1, 2, tzinfo=UTC),
    ) -> Field:
        """Build an ordinal field."""
        return self._build(
            id=id,
            user_id=user_id,
            version_id=version_id,
            name=name,
            type=FieldType.ORDINAL,
            config=OrdinalConfig(options),
            status=status,
            is_core=False,
            sort_order=sort_order,
            display_config=display_config,
            created_at=created_at,
        )

    def text(
        self,
        *,
        id: UUID | None = None,
        user_id: UUID | None = None,
        version_id: UUID | None = None,
        name: str = "Комментарий",
        status: FieldStatus = FieldStatus.ACTIVE,
        sort_order: int = 0,
        display_config: FieldDisplayConfig | None = None,
        created_at: datetime = datetime(2025, 1, 2, tzinfo=UTC),
    ) -> Field:
        """Build a free-text field."""
        return self._build(
            id=id,
            user_id=user_id,
            version_id=version_id,
            name=name,
            type=FieldType.TEXT,
            config=TextConfig(),
            status=status,
            is_core=False,
            sort_order=sort_order,
            display_config=display_config,
            created_at=created_at,
        )

    @staticmethod
    def _build(
        *,
        id: UUID | None,
        user_id: UUID | None,
        version_id: UUID | None,
        name: str,
        type: FieldType,
        config: FieldConfig,
        status: FieldStatus,
        is_core: bool,
        sort_order: int,
        display_config: FieldDisplayConfig | None,
        created_at: datetime,
    ) -> Field:
        field_id = id or uuid7()
        version = FieldVersion(
            id=version_id or uuid7(),
            field_id=field_id,
            type=type,
            config=config,
            created_at=created_at,
        )
        return Field(
            id=field_id,
            user_id=user_id or uuid7(),
            name=name,
            status=status,
            is_core=is_core,
            sort_order=sort_order,
            display_config=display_config or FieldDisplayConfig(),
            current_version=version,
        )

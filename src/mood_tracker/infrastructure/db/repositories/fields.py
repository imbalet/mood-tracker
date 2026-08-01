"""Field and field-version repository."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.domain.entities import EventFieldConfig, Field
from mood_tracker.domain.enums import FieldStatus
from mood_tracker.infrastructure.db.models import (
    EventFieldOrm,
    FieldOrm,
    FieldVersionOrm,
)
from mood_tracker.infrastructure.db.repositories._mapping import (
    display_from_json,
    display_to_json,
    version_from_orm,
    version_to_orm,
)


class SqlAlchemyFieldRepository:
    """Persist fields together with their immutable versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, field_id: UUID) -> Field | None:
        row = await self._session.scalar(
            select(FieldOrm).where(FieldOrm.id == field_id, FieldOrm.user_id == user_id)
        )
        return await self._to_domain(row) if row else None

    async def list_for_user(self, user_id: UUID) -> Sequence[Field]:
        rows = (
            await self._session.scalars(
                select(FieldOrm)
                .where(FieldOrm.user_id == user_id)
                .order_by(FieldOrm.sort_order)
            )
        ).all()
        return [await self._to_domain(row) for row in rows]

    async def add(self, field: Field) -> None:
        # Flush a newly registered user before inserting its fields.
        await self._session.flush()
        self._session.add(
            FieldOrm(
                id=field.id,
                user_id=field.user_id,
                name=field.name,
                status=field.status.value,
                is_core=field.is_core,
                current_version_id=field.current_version_id,
                sort_order=field.sort_order,
                display_config=display_to_json(field.display_config),
            )
        )
        for version in field.versions:
            self._session.add(version_to_orm(version))
        if field.event_config is not None:
            self._session.add(
                EventFieldOrm(
                    field_id=field.id,
                    required=field.event_config.required,
                    sort_order=field.event_config.sort_order,
                    is_system=field.event_config.is_system,
                )
            )

    async def save(self, field: Field) -> None:
        row = await self._session.get(FieldOrm, field.id)
        if row is None:
            return
        (
            row.name,
            row.status,
            row.current_version_id,
            row.sort_order,
            row.display_config,
        ) = (
            field.name,
            field.status.value,
            field.current_version_id,
            field.sort_order,
            display_to_json(field.display_config),
        )
        known_version_ids = set(
            (
                await self._session.scalars(
                    select(FieldVersionOrm.id).where(
                        FieldVersionOrm.field_id == field.id
                    )
                )
            ).all()
        )
        for version in field.versions:
            if version.id not in known_version_ids:
                self._session.add(version_to_orm(version))
        config = await self._session.get(EventFieldOrm, field.id)
        if field.event_config is None:
            if config is not None:
                await self._session.delete(config)
        elif config is None:
            self._session.add(
                EventFieldOrm(
                    field_id=field.id,
                    required=field.event_config.required,
                    sort_order=field.event_config.sort_order,
                    is_system=field.event_config.is_system,
                )
            )
        else:
            config.required = field.event_config.required
            config.sort_order = field.event_config.sort_order
            config.is_system = field.event_config.is_system

    async def _to_domain(self, row: FieldOrm) -> Field:
        version_rows = (
            await self._session.scalars(
                select(FieldVersionOrm)
                .where(FieldVersionOrm.field_id == row.id)
                .order_by(FieldVersionOrm.created_at)
            )
        ).all()
        versions = [version_from_orm(version) for version in version_rows]
        current_version = next(
            version for version in versions if version.id == row.current_version_id
        )
        event_config = await self._session.get(EventFieldOrm, row.id)
        return Field(
            row.id,
            row.user_id,
            row.name,
            FieldStatus(row.status),
            row.is_core,
            row.sort_order,
            display_from_json(row.display_config),
            current_version,
            versions,
            (
                EventFieldConfig(
                    event_config.required,
                    event_config.sort_order,
                    event_config.is_system,
                )
                if event_config is not None
                else None
            ),
        )


__all__ = ["SqlAlchemyFieldRepository"]

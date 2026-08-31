"""Field and field-version repository."""

from collections.abc import Sequence
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.application.ports import FieldRepository
from mood_tracker.domain.entities import Field
from mood_tracker.infrastructure.db.models import (
    FieldOrm,
    FieldVersionOrm,
)
from mood_tracker.infrastructure.db.repositories._mapping import (
    display_from_json,
    display_to_json,
    version_from_orm,
    version_to_orm,
)


class SqlAlchemyFieldRepository(FieldRepository):
    """Persist fields together with their immutable versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get(self, user_id: UUID, field_id: UUID) -> Field | None:
        row = await self._session.scalar(
            select(FieldOrm).where(
                FieldOrm.id == field_id,
                FieldOrm.user_id == user_id,
            )
        )
        return await self._to_domain(row) if row else None

    @override
    async def list_for_user(self, user_id: UUID) -> Sequence[Field]:
        rows = (
            await self._session.scalars(
                select(FieldOrm)
                .where(FieldOrm.user_id == user_id)
                .order_by(FieldOrm.name)
            )
        ).all()
        return [await self._to_domain(row) for row in rows]

    @override
    async def add(self, field: Field) -> None:
        # Flush a newly registered user before inserting its fields.
        await self._session.flush()
        self._session.add(
            FieldOrm(
                id=field.id,
                user_id=field.user_id,
                name=field.name,
                current_version_id=field.current_version_id,
                display_config=display_to_json(field.display_config),
            )
        )
        for version in field.versions:
            self._session.add(version_to_orm(version))

    @override
    async def save(self, field: Field) -> None:
        row = await self._session.get(FieldOrm, field.id)
        if row is None:
            return
        (
            row.name,
            row.current_version_id,
            row.display_config,
        ) = (
            field.name,
            field.current_version_id,
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
        return Field(
            row.id,
            row.user_id,
            row.name,
            display_from_json(row.display_config),
            current_version,
            versions,
        )

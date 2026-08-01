"""Questionnaire aggregate repository."""

from uuid import UUID, uuid7

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mood_tracker.domain.entities import Questionnaire, QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.infrastructure.db.models import (
    QuestionnaireFieldOrm,
    QuestionnaireOrm,
)


class SqlAlchemyQuestionnaireRepository:
    """Persist independent field placements for each built-in questionnaire."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, kind: QuestionnaireKind) -> Questionnaire | None:
        row = await self._session.scalar(
            select(QuestionnaireOrm).where(
                QuestionnaireOrm.user_id == user_id, QuestionnaireOrm.kind == kind.value
            )
        )
        return await self._to_domain(row) if row is not None else None

    async def add(self, questionnaire: Questionnaire) -> None:
        self._session.add(
            QuestionnaireOrm(
                id=questionnaire.id,
                user_id=questionnaire.user_id,
                kind=questionnaire.kind.value,
            )
        )
        await self._session.flush()
        await self._save_fields(questionnaire)

    async def save(self, questionnaire: Questionnaire) -> None:
        row = await self._session.get(QuestionnaireOrm, questionnaire.id)
        if row is None or row.user_id != questionnaire.user_id:
            return
        await self._save_fields(questionnaire)

    async def _save_fields(self, questionnaire: Questionnaire) -> None:
        existing = {
            row.field_id: row
            for row in (
                await self._session.scalars(
                    select(QuestionnaireFieldOrm).where(
                        QuestionnaireFieldOrm.questionnaire_id == questionnaire.id
                    )
                )
            ).all()
        }
        for placement in questionnaire.fields.values():
            row = existing.pop(placement.field_id, None)
            if row is None:
                self._session.add(
                    QuestionnaireFieldOrm(
                        id=uuid7(),
                        questionnaire_id=questionnaire.id,
                        field_id=placement.field_id,
                        sort_order=placement.sort_order,
                        is_enabled=placement.is_enabled,
                        is_required=placement.is_required,
                        role=placement.role.value,
                    )
                )
            else:
                row.sort_order = placement.sort_order
                row.is_enabled = placement.is_enabled
                row.is_required = placement.is_required
                row.role = placement.role.value
        for row in existing.values():
            await self._session.delete(row)

    async def _to_domain(self, row: QuestionnaireOrm) -> Questionnaire:
        field_rows = (
            await self._session.scalars(
                select(QuestionnaireFieldOrm)
                .where(QuestionnaireFieldOrm.questionnaire_id == row.id)
                .order_by(QuestionnaireFieldOrm.sort_order)
            )
        ).all()
        return Questionnaire(
            id=row.id,
            user_id=row.user_id,
            kind=QuestionnaireKind(row.kind),
            fields={
                field.field_id: QuestionnaireField(
                    field_id=field.field_id,
                    sort_order=field.sort_order,
                    is_enabled=field.is_enabled,
                    is_required=field.is_required,
                    role=QuestionnaireFieldRole(field.role),
                )
                for field in field_rows
            },
        )


__all__ = ["SqlAlchemyQuestionnaireRepository"]

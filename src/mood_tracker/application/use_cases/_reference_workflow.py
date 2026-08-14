"""Application workflow for reference-day decisions."""

from dataclasses import dataclass
from uuid import UUID

from mood_tracker.application.contracts.diary import ReferenceReview
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.domain.entities import Day, Field, ReferenceDays, ScaleConfig
from mood_tracker.domain.entities.reference_days import (
    boundary_reference_candidate,
    is_reference_boundary,
)
from mood_tracker.domain.enums import ReferenceType


@dataclass(frozen=True, slots=True)
class ReferenceUpdate:
    """The reference aggregate mutation produced by one workflow scenario."""

    changed: bool
    review: ReferenceReview | None = None
    reference_days: ReferenceDays | None = None


class ReferenceWorkflow:
    """Coordinate reference rules while keeping persistence in use cases."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def on_state_saved(
        self, user_id: UUID, day: Day, core_field: Field
    ) -> ReferenceUpdate:
        """Reconcile edited references and evaluate a newly saved state value."""
        reference_days = await self._uow.reference_days.get(user_id)
        if reference_days is None:
            reference_days = ReferenceDays(user_id=user_id)
        if not reference_days.has_history:
            reference_days.initialize(
                day.id,
                self._id_generator.new(),
                self._id_generator.new(),
                self._clock.now(),
            )
            return ReferenceUpdate(True, reference_days=reference_days)

        valid_ids = await self._valid_day_ids_by_type(
            user_id, core_field, reference_days
        )
        changed = self._reconcile_current_references(
            day, core_field, reference_days, valid_ids
        )
        candidate_type = self._candidate_type(day, core_field)
        if candidate_type is None:
            return ReferenceUpdate(changed, reference_days=reference_days)

        previous_day_id = reference_days.current_day_id(candidate_type)
        if previous_day_id is None:
            reference_days.establish_baseline(
                self._id_generator.new(), day.id, candidate_type, self._clock.now()
            )
            return ReferenceUpdate(True, reference_days=reference_days)
        if previous_day_id == day.id:
            return ReferenceUpdate(changed, reference_days=reference_days)
        if not valid_ids[candidate_type]:
            reference_days.apply_confirmed_change(
                self._id_generator.new(), day.id, candidate_type, self._clock.now()
            )
            return ReferenceUpdate(True, reference_days=reference_days)
        return ReferenceUpdate(
            changed,
            ReferenceReview(day.id, candidate_type, previous_day_id),
            reference_days,
        )

    async def confirm(
        self,
        user_id: UUID,
        day: Day,
        core_field: Field,
        reference_type: ReferenceType,
        is_new_record: bool,
    ) -> ReferenceUpdate:
        """Apply an idempotent confirmation or rejection of a proposed change."""
        reference_days = await self._uow.reference_days.get(user_id)
        if reference_days is None or not is_reference_boundary(
            day, core_field, reference_type
        ):
            return ReferenceUpdate(False)

        current_day_id = reference_days.current_day_id(reference_type)
        if is_new_record:
            if current_day_id is None:
                reference_days.establish_baseline(
                    self._id_generator.new(),
                    day.id,
                    reference_type,
                    self._clock.now(),
                )
            elif current_day_id != day.id:
                reference_days.apply_confirmed_change(
                    self._id_generator.new(),
                    day.id,
                    reference_type,
                    self._clock.now(),
                )
            else:
                return ReferenceUpdate(False)
            return ReferenceUpdate(True, reference_days=reference_days)

        if current_day_id != day.id:
            return ReferenceUpdate(False)
        valid_ids = await self._valid_day_ids_by_type(
            user_id, core_field, reference_days
        )
        reference_days.rollback_current(
            reference_type, valid_ids[reference_type].__contains__
        )
        return ReferenceUpdate(True, reference_days=reference_days)

    async def _valid_day_ids_by_type(
        self, user_id: UUID, core_field: Field, reference_days: ReferenceDays
    ) -> dict[ReferenceType, set[UUID]]:
        """Load history once and classify which recorded references remain valid."""
        day_ids = tuple({reference.day_id for reference in reference_days.history})
        days = await self._uow.days.get_many(user_id, day_ids)
        return {
            reference_type: {
                day.id
                for day in days
                if is_reference_boundary(day, core_field, reference_type)
            }
            for reference_type in ReferenceType
        }

    @staticmethod
    def _reconcile_current_references(
        day: Day,
        core_field: Field,
        reference_days: ReferenceDays,
        valid_ids: dict[ReferenceType, set[UUID]],
    ) -> bool:
        """Restore pointers whose edited current day is no longer a boundary."""
        changed = False
        for reference_type in ReferenceType:
            if reference_days.current_day_id(
                reference_type
            ) == day.id and not is_reference_boundary(day, core_field, reference_type):
                reference_days.rollback_current(
                    reference_type, valid_ids[reference_type].__contains__
                )
                changed = True
        return changed

    @staticmethod
    def _candidate_type(day: Day, core_field: Field) -> ReferenceType | None:
        """Return the boundary type for the newly saved current field value."""
        answer = day.response.answers.get(core_field.id)
        if answer is None or not isinstance(answer.value, int):
            return None
        config = core_field.current_version.config
        if not isinstance(config, ScaleConfig):
            return None
        return boundary_reference_candidate(answer.value, config)

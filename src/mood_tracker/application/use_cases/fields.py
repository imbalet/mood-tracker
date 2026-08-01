"""Use cases for mutable field presentation and semantic versions."""

from uuid import UUID

from mood_tracker.application.commands import (
    AddFieldVersion,
    CreateField,
    ListFields,
    MoveDirection,
    MoveField,
    RenameField,
    SetFieldDisplay,
    SetFieldSortOrder,
    SetFieldStatus,
)
from mood_tracker.application.errors import FieldNotFound, UserNotFound
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import Field, FieldVersion
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.domain.errors import InvalidFieldVersion


async def _get_owned_field(uow: UnitOfWork, user_id: UUID, field_id: UUID) -> Field:
    field = await uow.fields.get(user_id, field_id)
    if field is None:
        raise FieldNotFound
    return field


async def _ensure_user_exists(uow: UnitOfWork, user_id: UUID) -> None:
    if await uow.users.get(user_id) is None:
        raise UserNotFound


class CreateFieldUseCase:
    """Create a user-owned custom field."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: CreateField) -> Field:
        """Create a field and its initial immutable semantic version."""

        async def operation() -> Field:
            await _ensure_user_exists(self._uow, command.user_id)
            field_id = self._id_generator.new()
            version = FieldVersion(
                id=self._id_generator.new(),
                field_id=field_id,
                type=command.config.field_type,
                config=command.config,
                created_at=self._clock.now(),
            )
            field = Field(
                id=field_id,
                user_id=command.user_id,
                name=command.name,
                display_config=command.display_config,
                current_version=version,
                questionnaire_fields={
                    QuestionnaireKind.DAY: QuestionnaireField(
                        field_id, command.sort_order
                    )
                },
            )
            await self._uow.fields.add(field)
            return field

        return await execute_write(self._uow, operation)


class ListFieldsUseCase:
    """Read user-owned fields in their configured order."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: ListFields) -> tuple[Field, ...]:
        """Return all fields only when the owner exists."""
        async with self._uow:
            await _ensure_user_exists(self._uow, command.user_id)
            return tuple(
                sorted(
                    await self._uow.fields.list_for_user(command.user_id),
                    key=lambda field: field.sort_order,
                )
            )


class RenameFieldUseCase:
    """Rename a user-owned field."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RenameField) -> Field:
        """Persist a display-name change."""

        async def operation() -> Field:
            field = await _get_owned_field(self._uow, command.user_id, command.field_id)
            field.rename(command.name)
            await self._uow.fields.save(field)
            return field

        return await execute_transaction(self._uow, operation)


class SetFieldStatusUseCase:
    """Change a field lifecycle state."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SetFieldStatus) -> Field:
        """Persist a lifecycle change while keeping core rules in domain."""

        async def operation() -> Field:
            field = await _get_owned_field(self._uow, command.user_id, command.field_id)
            field.set_status(command.status)
            await self._uow.fields.save(field)
            return field

        return await execute_transaction(self._uow, operation)


class SetFieldDisplayUseCase:
    """Change global visual field settings."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SetFieldDisplay) -> Field:
        """Persist display-only configuration without making a new version."""

        async def operation() -> Field:
            field = await _get_owned_field(self._uow, command.user_id, command.field_id)
            field.set_display_config(command.display_config)
            await self._uow.fields.save(field)
            return field

        return await execute_transaction(self._uow, operation)


class SetFieldSortOrderUseCase:
    """Change one field's position."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: SetFieldSortOrder) -> Field:
        """Persist a new sort order."""

        async def operation() -> Field:
            field = await _get_owned_field(self._uow, command.user_id, command.field_id)
            field.set_sort_order(command.sort_order)
            await self._uow.fields.save(field)
            return field

        return await execute_transaction(self._uow, operation)


class MoveFieldUseCase:
    """Move a field while keeping every user order unique and contiguous."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: MoveField) -> tuple[Field, ...]:
        """Swap one field with its neighbour and persist normalized positions."""

        async def operation() -> tuple[Field, ...]:
            await _ensure_user_exists(self._uow, command.user_id)
            fields = list(
                sorted(
                    await self._uow.fields.list_for_user(command.user_id),
                    key=lambda field: (field.sort_order, str(field.id)),
                )
            )
            current_index = next(
                (
                    index
                    for index, field in enumerate(fields)
                    if field.id == command.field_id
                ),
                None,
            )
            if current_index is None:
                raise FieldNotFound
            target_index = current_index + (
                -1 if command.direction is MoveDirection.UP else 1
            )
            if 0 <= target_index < len(fields):
                fields[current_index], fields[target_index] = (
                    fields[target_index],
                    fields[current_index],
                )
            for index, field in enumerate(fields):
                if field.sort_order != index:
                    field.set_sort_order(index)
                    await self._uow.fields.save(field)
            return tuple(fields)

        return await execute_transaction(self._uow, operation)


class AddFieldVersionUseCase:
    """Append a semantic version to an existing field."""

    def __init__(
        self, uow: UnitOfWork, clock: Clock, id_generator: IdGenerator
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def execute(self, command: AddFieldVersion) -> Field:
        """Make a new semantic field version current."""

        async def operation() -> Field:
            field = await _get_owned_field(self._uow, command.user_id, command.field_id)
            if command.config.field_type is not field.current_version.type:
                msg = "A new field version must retain the original field type"
                raise InvalidFieldVersion(msg)
            version = FieldVersion(
                id=self._id_generator.new(),
                field_id=field.id,
                type=command.config.field_type,
                config=command.config,
                created_at=self._clock.now(),
            )
            field.add_version(version)
            await self._uow.fields.save(field)
            return field

        return await execute_write(self._uow, operation)

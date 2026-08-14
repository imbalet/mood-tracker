"""Use cases for mutable field presentation and semantic versions."""

from mood_tracker.application.contracts.questionnaires import (
    AddFieldVersion,
    AttachFieldToQuestionnaire,
    CreateField,
    DeleteField,
    DetachFieldFromQuestionnaire,
    ListQuestionnaireFields,
    MoveQuestionnaireField,
    QuestionnaireFieldItem,
    RenameField,
    SetFieldDisplay,
    SetQuestionnaireFieldEnabled,
    SetQuestionnaireFieldRequired,
)
from mood_tracker.application.ports import Clock, IdGenerator, UnitOfWork
from mood_tracker.application.use_cases._loaders import (
    list_questionnaire_fields,
    require_owned_field,
    require_questionnaire,
    require_user,
)
from mood_tracker.application.use_cases._transactions import (
    execute_transaction,
    execute_write,
)
from mood_tracker.domain.entities import Field, FieldVersion
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.domain.errors import CoreFieldViolation


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
            await require_user(self._uow, command.user_id)
            field_id = self._id_generator.new()
            version = FieldVersion(
                id=self._id_generator.new(),
                field_id=field_id,
                config=command.config,
                created_at=self._clock.now(),
            )
            field = Field(
                id=field_id,
                user_id=command.user_id,
                name=command.name,
                display_config=command.display_config,
                current_version=version,
            )
            await self._uow.fields.add(field)
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.attach(field.id, is_required=True)
            await self._uow.questionnaires.save(questionnaire)
            return field

        return await execute_write(self._uow, operation)


class RenameFieldUseCase:
    """Rename a user-owned field."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RenameField) -> Field:
        """Persist a display-name change."""

        async def operation() -> Field:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            field.rename(command.name)
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
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            field.set_display_config(command.display_config)
            await self._uow.fields.save(field)
            return field

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
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            version = FieldVersion(
                id=self._id_generator.new(),
                field_id=field.id,
                config=command.config,
                created_at=self._clock.now(),
            )
            field.add_version(version)
            await self._uow.fields.save(field)
            return field

        return await execute_write(self._uow, operation)


class QuestionnaireFieldUseCase:
    """Configure a field's participation in an explicitly selected questionnaire."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def attach(self, command: AttachFieldToQuestionnaire) -> Field:
        async def operation() -> Field:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.attach(command.field_id, is_required=command.is_required)
            await self._uow.questionnaires.save(questionnaire)
            return field

        return await execute_transaction(self._uow, operation)

    async def detach(self, command: DetachFieldFromQuestionnaire) -> Field:
        async def operation() -> Field:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.detach(field.id)
            await self._uow.questionnaires.save(questionnaire)
            return field

        return await execute_transaction(self._uow, operation)

    async def set_enabled(self, command: SetQuestionnaireFieldEnabled) -> Field:
        async def operation() -> Field:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.set_enabled(field.id, command.is_enabled)
            await self._uow.questionnaires.save(questionnaire)
            return field

        return await execute_transaction(self._uow, operation)

    async def set_required(self, command: SetQuestionnaireFieldRequired) -> Field:
        async def operation() -> Field:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.set_required(field.id, command.is_required)
            await self._uow.questionnaires.save(questionnaire)
            return field

        return await execute_transaction(self._uow, operation)

    async def move(
        self, command: MoveQuestionnaireField
    ) -> tuple[QuestionnaireFieldItem, ...]:
        """Move one placement and normalize only that questionnaire's order."""

        async def operation() -> tuple[QuestionnaireFieldItem, ...]:
            await require_owned_field(self._uow, command.user_id, command.field_id)
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            questionnaire.move(command.field_id, command.direction)
            await self._uow.questionnaires.save(questionnaire)
            return await list_questionnaire_fields(
                self._uow, command.user_id, questionnaire
            )

        return await execute_transaction(self._uow, operation)

    async def delete(self, command: DeleteField) -> None:
        async def operation() -> None:
            field = await require_owned_field(
                self._uow, command.user_id, command.field_id
            )
            for kind in QuestionnaireKind:
                questionnaire = await self._uow.questionnaires.get(
                    command.user_id, kind
                )
                placement = (
                    questionnaire.fields.get(field.id) if questionnaire else None
                )
                if (
                    placement is not None
                    and placement.role is not QuestionnaireFieldRole.ORDINARY
                ):
                    msg = "System questionnaire field cannot be deleted"
                    raise CoreFieldViolation(msg)
            field.delete(self._clock.now())
            await self._uow.fields.save(field)

        await execute_transaction(self._uow, operation)


class ListQuestionnaireFieldsUseCase:
    """List the fields assigned to one questionnaire in its own order."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, command: ListQuestionnaireFields
    ) -> tuple[QuestionnaireFieldItem, ...]:
        async with self._uow:
            await require_user(self._uow, command.user_id)
            questionnaire = await require_questionnaire(
                self._uow, command.user_id, command.kind
            )
            return await list_questionnaire_fields(
                self._uow, command.user_id, questionnaire
            )

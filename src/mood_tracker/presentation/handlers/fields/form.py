"""Creation, renaming and semantic-version forms for diary fields."""

from html import escape
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import (
    AddFieldVersion,
    CreateField,
    ListQuestionnaireFields,
    RenameField,
)
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.domain.entities import (
    Field,
    FieldDisplayConfig,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
    TextConfig,
    UserProfile,
)
from mood_tracker.domain.enums import FieldType, QuestionnaireKind
from mood_tracker.domain.errors import InvalidFieldVersion
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldCreateCallback,
    OrdinalBaseCallback,
    OrdinalDraftAction,
    OrdinalDraftCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.handlers.fields.common import (
    invalidate_form,
    render_field,
    render_fields,
    show_input_error,
)
from mood_tracker.presentation.keyboards import (
    ordinal_base_keyboard,
    ordinal_draft_keyboard,
)
from mood_tracker.presentation.queries import get_owned_field, get_user_profile
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import (
    CreateFieldConfigData,
    CreateFieldNameData,
    CreateOrdinalData,
    FieldCreation,
    FieldRename,
    FieldVersionChange,
    FieldVersionData,
    InvalidPresentationData,
    PresentationData,
    RenameFieldData,
    VersionOrdinalData,
)
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="fields_form")


@router.callback_query(FieldCreateCallback.filter())
async def start_create_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldCreateCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Store the selected type and ask for a new field name."""
    await state.set_state(FieldCreation.waiting_name)
    await presentation_data.write(
        CreateFieldNameData(callback_data.type, callback_data.kind)
    )
    await query.answer()
    await update_main_message(
        presentation_data, query, TEXTS[TextKey.FIELD_NAME_PROMPT]
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.RENAME))
async def prompt_rename(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Collect a replacement display name."""
    await state.set_state(FieldRename.waiting_name)
    await presentation_data.write(RenameFieldData(callback_data.field_id))
    await query.answer()
    await update_main_message(
        presentation_data, query, TEXTS[TextKey.FIELD_NAME_PROMPT]
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.VERSION))
async def prompt_new_version(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Ask for a same-type semantic configuration."""
    profile = await get_user_profile(telegram_id, services)
    field = (
        await get_owned_field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    if field is None or field.current_version.type is FieldType.TEXT:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await presentation_data.write(FieldVersionData(field.id))
    await query.answer()
    if field.current_version.type is FieldType.SCALE:
        await state.set_state(FieldVersionChange.waiting_scale)
        await update_main_message(presentation_data, query, TEXTS[TextKey.SCALE_PROMPT])
        return
    await state.set_state(FieldVersionChange.waiting_ordinal_base)
    await update_main_message(
        presentation_data,
        query,
        TEXTS[TextKey.ORDINAL_BASE_PROMPT],
        reply_markup=ordinal_base_keyboard(),
    )


@router.message(FieldCreation.waiting_name, F.text)
async def save_new_field_name(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Advance a new field to its type-specific configuration step."""
    try:
        form = await presentation_data.require(CreateFieldNameData)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    if not (name := (message.text or "").strip()):
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.INVALID_FIELD_INPUT]
        )
        return
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await state.set_state(None)
        await presentation_data.clear_flow()
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.START_FIRST]
        )
        return
    if form.field_type is FieldType.TEXT:
        await _create_field(profile, name, TextConfig(), form.kind_value, services)
        await state.set_state(None)
        await presentation_data.clear_flow()
        await render_fields(
            message,
            presentation_data,
            profile,
            services,
            update_main_message,
            form.kind_value,
        )
        return
    await presentation_data.write(
        CreateFieldConfigData(form.field_type, name, form.kind_value)
    )
    if form.field_type is FieldType.SCALE:
        await state.set_state(FieldCreation.waiting_scale)
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.SCALE_PROMPT]
        )
        return
    await state.set_state(FieldCreation.waiting_ordinal_base)
    await update_main_message(
        presentation_data,
        message,
        TEXTS[TextKey.ORDINAL_BASE_PROMPT],
        reply_markup=ordinal_base_keyboard(),
    )


@router.message(FieldRename.waiting_name, F.text)
async def save_renamed_field(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a replacement name for one owned field."""
    try:
        form = await presentation_data.require(RenameFieldData)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    if not (name := (message.text or "").strip()):
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.INVALID_FIELD_INPUT]
        )
        return
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    try:
        field = await services.rename_field().execute(
            RenameField(profile.id, form.field_id, name)
        )
    except FieldNotFound, InvalidFieldVersion:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_field(message, presentation_data, field, update_main_message)


@router.message(FieldCreation.waiting_scale, F.text)
@router.message(FieldVersionChange.waiting_scale, F.text)
async def save_scale_config(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist the Scale configuration for its explicit active flow."""
    try:
        minimum, maximum = (int(value) for value in (message.text or "").split())
        config = ScaleConfig(minimum, maximum)
    except TypeError, ValueError, InvalidFieldVersion:
        await show_input_error(
            presentation_data,
            message,
            update_main_message,
            TEXTS[TextKey.INVALID_SCALE_INPUT],
            TEXTS[TextKey.SCALE_PROMPT],
        )
        return
    try:
        created = await presentation_data.require(CreateFieldConfigData)
    except InvalidPresentationData:
        created = None
    if created is not None and created.field_type is FieldType.SCALE:
        await _finish_created_config(
            message,
            state,
            presentation_data,
            telegram_id,
            services,
            update_main_message,
            created.name,
            config,
            created.kind_value,
        )
        return
    try:
        version = await presentation_data.require(FieldVersionData)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    await _finish_version_config(
        message,
        state,
        presentation_data,
        telegram_id,
        services,
        update_main_message,
        version.field_id,
        config,
    )


@router.callback_query(OrdinalBaseCallback.filter())
async def choose_ordinal_base(
    query: CallbackQueryWithMessage,
    callback_data: OrdinalBaseCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Start the ordinal editor for creation or a new version."""
    try:
        created = await presentation_data.require(CreateFieldConfigData)
    except InvalidPresentationData:
        created = None
    if created is not None and created.field_type is FieldType.ORDINAL:
        await state.set_state(FieldCreation.waiting_ordinal_label)
        await presentation_data.write(
            CreateOrdinalData(created.name, callback_data.value, (), created.kind_value)
        )
    else:
        try:
            version = await presentation_data.require(FieldVersionData)
        except InvalidPresentationData:
            await invalidate_form(state, presentation_data, query, update_main_message)
            return
        await state.set_state(FieldVersionChange.waiting_ordinal_label)
        await presentation_data.write(
            VersionOrdinalData(version.field_id, callback_data.value, ())
        )
    await query.answer()
    await _render_ordinal_draft(query, presentation_data, update_main_message)


@router.message(FieldCreation.waiting_ordinal_label, F.text)
@router.message(FieldVersionChange.waiting_ordinal_label, F.text)
async def add_ordinal_label(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Append one label to the typed ordinal draft."""
    try:
        draft = await _ordinal_draft(presentation_data)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    label = (message.text or "").strip()
    if not label or "\n" in label:
        await _render_ordinal_draft(
            message,
            presentation_data,
            update_main_message,
            draft,
            error=TEXTS[TextKey.INVALID_FIELD_INPUT],
        )
        return
    await presentation_data.write(_with_labels(draft, (*draft.labels, label)))
    await _render_ordinal_draft(message, presentation_data, update_main_message)


@router.callback_query(OrdinalDraftCallback.filter())
async def edit_ordinal_draft(
    query: CallbackQueryWithMessage,
    callback_data: OrdinalDraftCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Modify or commit the ordinal draft belonging to the current flow."""
    try:
        draft = await _ordinal_draft(presentation_data)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, query, update_main_message)
        return
    if callback_data.action is OrdinalDraftAction.REMOVE:
        await presentation_data.write(_with_labels(draft, draft.labels[:-1]))
        await query.answer()
        await _render_ordinal_draft(query, presentation_data, update_main_message)
        return
    if callback_data.action is OrdinalDraftAction.RESET:
        await presentation_data.write(_with_labels(draft, ()))
        await query.answer()
        await _render_ordinal_draft(query, presentation_data, update_main_message)
        return
    if len(draft.labels) < 2:
        await query.answer(TEXTS[TextKey.INVALID_FIELD_INPUT], show_alert=True)
        return
    config = OrdinalConfig(
        tuple(
            OrdinalOption(draft.starts_at + index, label)
            for index, label in enumerate(draft.labels)
        )
    )
    await query.answer()
    if isinstance(draft, CreateOrdinalData):
        await _finish_created_config(
            query,
            state,
            presentation_data,
            telegram_id,
            services,
            update_main_message,
            draft.name,
            config,
            draft.kind_value,
        )
    else:
        await _finish_version_config(
            query,
            state,
            presentation_data,
            telegram_id,
            services,
            update_main_message,
            draft.field_id,
            config,
        )


async def _finish_created_config(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
    name: str,
    config: ScaleConfig | OrdinalConfig,
    kind: QuestionnaireKind,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await invalidate_form(state, presentation_data, event, update_main_message)
        return
    await _create_field(profile, name, config, kind, services)
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_fields(
        event, presentation_data, profile, services, update_main_message, kind
    )


async def _finish_version_config(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
    field_id: UUID,
    config: ScaleConfig | OrdinalConfig,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await invalidate_form(state, presentation_data, event, update_main_message)
        return
    try:
        field = await services.add_field_version().execute(
            AddFieldVersion(profile.id, field_id, config)
        )
    except FieldNotFound, InvalidFieldVersion:
        await invalidate_form(state, presentation_data, event, update_main_message)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_field(event, presentation_data, field, update_main_message)


async def _create_field(
    profile: UserProfile,
    name: str,
    config: ScaleConfig | OrdinalConfig | TextConfig,
    kind: QuestionnaireKind,
    services: ApplicationServices,
) -> Field:
    fields = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, kind)
    )
    return await services.create_field().execute(
        CreateField(
            profile.id,
            name,
            config,
            FieldDisplayConfig(),
            sort_order=len(fields),
            kind=kind,
        )
    )


async def _ordinal_draft(
    presentation_data: PresentationData,
) -> CreateOrdinalData | VersionOrdinalData:
    try:
        return await presentation_data.require(CreateOrdinalData)
    except InvalidPresentationData:
        draft = await presentation_data.require(VersionOrdinalData)
        return draft


def _with_labels(
    draft: CreateOrdinalData | VersionOrdinalData, labels: tuple[str, ...]
) -> CreateOrdinalData | VersionOrdinalData:
    if isinstance(draft, CreateOrdinalData):
        return CreateOrdinalData(draft.name, draft.starts_at, labels, draft.kind_value)
    return VersionOrdinalData(draft.field_id, draft.starts_at, labels)


async def _render_ordinal_draft(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
    draft: CreateOrdinalData | VersionOrdinalData | None = None,
    *,
    error: str | None = None,
) -> None:
    if draft is None:
        draft = await _ordinal_draft(presentation_data)
    options = (
        "\n".join(
            f"{index}. {escape(label)}"
            for index, label in enumerate(draft.labels, start=1)
        )
        or "—"
    )
    prompt = (
        TEXTS[TextKey.ORDINAL_NEXT_PROMPT]
        if draft.labels
        else TEXTS[TextKey.ORDINAL_FIRST_PROMPT]
    )
    text = "\n\n".join(
        part
        for part in (
            error,
            TEXTS[TextKey.ORDINAL_DRAFT].format(options=options),
            prompt,
        )
        if part
    )
    await update_main_message(
        presentation_data,
        event,
        text,
        reply_markup=ordinal_draft_keyboard(len(draft.labels)),
    )

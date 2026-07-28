"""Inline management of custom diary fields and their versions."""

from html import escape
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import (
    AddFieldVersion,
    CreateField,
    GetUserByTelegramId,
    ListFields,
    MoveField,
    RenameField,
    SetFieldDisplay,
    SetFieldStatus,
)
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.domain.entities import (
    Field,
    FieldDisplayConfig,
    OrdinalConfig,
    OrdinalOption,
    ScaleConfig,
    StatePalette,
    TextConfig,
    UserProfile,
)
from mood_tracker.domain.enums import FieldType
from mood_tracker.domain.errors import (
    CoreFieldViolation,
    InvalidFieldVersion,
)
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldCreateCallback,
    FieldMoveCallback,
    FieldsListAction,
    FieldsListCallback,
    FieldStatusCallback,
    MenuCallback,
    MenuSection,
    OrdinalBaseCallback,
    OrdinalDraftAction,
    OrdinalDraftCallback,
    PaletteCallback,
    PalettePreset,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.formatters import (
    format_field_card,
    format_fields_list,
    format_palette_message,
)
from mood_tracker.presentation.keyboards import (
    field_card_keyboard,
    field_order_keyboard,
    field_type_keyboard,
    fields_keyboard,
    ordinal_base_keyboard,
    ordinal_draft_keyboard,
    palette_keyboard,
)
from mood_tracker.presentation.palettes import PALETTES
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.states import FieldForm
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="fields")


@router.callback_query(MenuCallback.filter(F.section == MenuSection.FIELDS))
async def open_fields(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open all field settings owned by the current Telegram user."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    await state.clear()
    await query.answer()
    await _render_fields(query, state, profile, services, update_main_message)


@router.callback_query(FieldsListCallback.filter(F.action == FieldsListAction.CREATE))
async def choose_field_type(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Show choices for a new custom field."""
    await state.clear()
    await query.answer()
    await update_main_message(
        state,
        query,
        TEXTS[TextKey.CREATE_FIELD_TYPE],
        reply_markup=field_type_keyboard(),
    )


@router.callback_query(FieldsListCallback.filter(F.action == FieldsListAction.ORDER))
async def open_order_from_fields(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the order editor before a field has been selected."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    fields = await services.list_fields().execute(ListFields(profile.id))
    await state.clear()
    await state.update_data(mode="order")
    await query.answer()
    await _render_order(query, state, fields, None, update_main_message)


@router.callback_query(FieldCreateCallback.filter())
async def start_create_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldCreateCallback,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Store the selected type and ask the user for the field name."""
    await state.set_state(FieldForm.waiting_name)
    await state.update_data(mode="create", field_type=callback_data.type.value)
    await query.answer()
    await update_main_message(state, query, TEXTS[TextKey.FIELD_NAME_PROMPT])


@router.callback_query(FieldCallback.filter(F.action == FieldAction.OPEN))
async def open_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open a field card after resolving it within the current owner scope."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    field = await _field(profile, callback_data.field_id, services)
    if field is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.clear()
    await query.answer()
    await _render_field(query, state, field, update_main_message)


@router.callback_query(FieldCallback.filter(F.action == FieldAction.RENAME))
async def prompt_rename(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Collect a replacement display name."""
    await state.set_state(FieldForm.waiting_name)
    await state.update_data(mode="rename", field_id=str(callback_data.field_id))
    await query.answer()
    await update_main_message(state, query, TEXTS[TextKey.FIELD_NAME_PROMPT])


@router.callback_query(FieldCallback.filter(F.action == FieldAction.VERSION))
async def prompt_new_version(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Ask for a same-type semantic configuration."""
    profile = await _profile(telegram_id, services)
    field = (
        await _field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    if field is None or field.current_version.type is FieldType.TEXT:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.update_data(mode="version", field_id=str(field.id))
    await query.answer()
    if field.current_version.type is FieldType.SCALE:
        await state.set_state(FieldForm.waiting_scale)
        await update_main_message(state, query, TEXTS[TextKey.SCALE_PROMPT])
        return
    await state.set_state(FieldForm.waiting_ordinal_base)
    await update_main_message(
        state,
        query,
        TEXTS[TextKey.ORDINAL_BASE_PROMPT],
        reply_markup=ordinal_base_keyboard(),
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.ORDER))
async def open_field_order(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open an inline list where a selected field moves in place."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    fields = await services.list_fields().execute(ListFields(profile.id))
    if not any(field.id == callback_data.field_id for field in fields):
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.clear()
    await state.update_data(mode="order", field_id=str(callback_data.field_id))
    await query.answer()
    await _render_order(
        query, state, fields, callback_data.field_id, update_main_message
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.EMOJI))
async def prompt_emoji(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Ask for a replacement emoji."""
    await state.set_state(FieldForm.waiting_emoji)
    await state.update_data(field_id=str(callback_data.field_id))
    await query.answer()
    await update_main_message(state, query, TEXTS[TextKey.EMOJI_PROMPT])


@router.callback_query(FieldCallback.filter(F.action == FieldAction.CLEAR_EMOJI))
async def clear_emoji(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Remove the global emoji while retaining other visual settings."""
    await _update_display(
        query,
        state,
        telegram_id,
        callback_data.field_id,
        services,
        update_main_message,
        emoji=None,
        update_emoji=True,
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.TOGGLE_CALENDAR))
async def toggle_calendar(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Toggle whether a field is offered to calendar renderers."""
    profile = await _profile(telegram_id, services)
    field = (
        await _field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    if field is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await _update_display(
        query,
        state,
        telegram_id,
        field.id,
        services,
        update_main_message,
        show_in_calendar=not field.display_config.show_in_calendar,
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.PALETTE))
async def choose_palette(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Show visual palette presets and the custom color route."""
    profile = await _profile(telegram_id, services)
    field = (
        await _field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    if field is None or not field.is_core:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.clear()
    palette = field.display_config.state_palette
    if not isinstance(field.current_version.config, ScaleConfig) or palette is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await _render_palette_selector(
        query,
        state,
        field,
        palette,
        update_main_message=update_main_message,
    )


@router.callback_query(PaletteCallback.filter())
async def save_palette_preset(
    query: CallbackQueryWithMessage,
    callback_data: PaletteCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Apply a preset or request exactly three custom HEX colors."""
    if callback_data.preset is PalettePreset.CUSTOM:
        await state.set_state(FieldForm.waiting_palette)
        await state.update_data(field_id=str(callback_data.field_id))
        await query.answer()
        await update_main_message(state, query, TEXTS[TextKey.PALETTE_PROMPT])
        return
    await _update_display(
        query,
        state,
        telegram_id,
        callback_data.field_id,
        services,
        update_main_message,
        state_palette=PALETTES[callback_data.preset],
        update_palette=True,
    )


@router.callback_query(FieldStatusCallback.filter())
async def set_status(
    query: CallbackQueryWithMessage,
    callback_data: FieldStatusCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Change lifecycle for an owned non-core field."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    try:
        field = await services.set_field_status().execute(
            SetFieldStatus(profile.id, callback_data.field_id, callback_data.status)
        )
    except FieldNotFound, CoreFieldViolation:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await query.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await _render_field(query, state, field, update_main_message)


@router.callback_query(FieldMoveCallback.filter())
async def move_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldMoveCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Move one field without creating ambiguous duplicate positions."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    current_fields = await services.list_fields().execute(ListFields(profile.id))
    current_index = next(
        (
            index
            for index, field in enumerate(current_fields)
            if field.id == callback_data.field_id
        ),
        None,
    )
    if current_index is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    if (callback_data.direction.value == "up" and current_index == 0) or (
        callback_data.direction.value == "down"
        and current_index == len(current_fields) - 1
    ):
        await query.answer()
        return
    try:
        fields = await services.move_field().execute(
            MoveField(profile.id, callback_data.field_id, callback_data.direction)
        )
    except FieldNotFound:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await query.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await state.update_data(mode="order", field_id=str(callback_data.field_id))
    await _render_order(
        query, state, fields, callback_data.field_id, update_main_message
    )


@router.message(FieldForm.waiting_name, F.text)
async def save_name(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Use a submitted name for a new field or an existing one."""
    name = (message.text or "").strip()
    data = await state.get_data()
    mode = data.get("mode")
    if not name or not isinstance(mode, str):
        await update_main_message(state, message, TEXTS[TextKey.INVALID_FIELD_INPUT])
        return
    profile = await _profile(telegram_id, services)
    if profile is None:
        await state.clear()
        await update_main_message(state, message, TEXTS[TextKey.START_FIRST])
        return
    if mode == "rename":
        field_id = _field_id(data)
        if field_id is None:
            await _invalid_form(state, message, update_main_message)
            return
        try:
            field = await services.rename_field().execute(
                RenameField(profile.id, field_id, name)
            )
        except FieldNotFound, InvalidFieldVersion:
            await _invalid_form(state, message, update_main_message)
            return
        await state.clear()
        await _render_field(message, state, field, update_main_message)
        return
    if mode != "create" or not isinstance(data.get("field_type"), str):
        await _invalid_form(state, message, update_main_message)
        return
    field_type = FieldType(data["field_type"])
    await state.update_data(name=name)
    if field_type is FieldType.TEXT:
        await _create_field(profile, name, TextConfig(), services)
        await state.clear()
        await _render_fields(message, state, profile, services, update_main_message)
        return
    if field_type is FieldType.ORDINAL:
        await state.set_state(FieldForm.waiting_ordinal_base)
        await update_main_message(
            state,
            message,
            TEXTS[TextKey.ORDINAL_BASE_PROMPT],
            reply_markup=ordinal_base_keyboard(),
        )
        return
    await state.set_state(FieldForm.waiting_scale)
    await update_main_message(
        state,
        message,
        TEXTS[TextKey.SCALE_PROMPT],
    )


@router.message(FieldForm.waiting_scale, F.text)
async def save_scale_config(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Parse a two-integer Scale configuration."""
    try:
        minimum, maximum = (int(value) for value in (message.text or "").split())
        config = ScaleConfig(minimum, maximum)
    except TypeError, ValueError, InvalidFieldVersion:
        await _show_input_error(
            state,
            message,
            update_main_message,
            TEXTS[TextKey.INVALID_SCALE_INPUT],
            TEXTS[TextKey.SCALE_PROMPT],
        )
        return
    await _save_config(
        message, state, telegram_id, services, update_main_message, config
    )


@router.callback_query(OrdinalBaseCallback.filter())
async def choose_ordinal_base(
    query: CallbackQueryWithMessage,
    callback_data: OrdinalBaseCallback,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Start a staged ordinal editor with the selected first stored value."""
    await state.set_state(FieldForm.waiting_ordinal)
    await state.update_data(ordinal_start=callback_data.value, ordinal_labels=[])
    await query.answer()
    await _render_ordinal_draft(query, state, update_main_message)


@router.message(FieldForm.waiting_ordinal, F.text)
async def add_ordinal_label(
    message: Message,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
) -> None:
    """Append one visible ordinal label without exposing internal values."""
    label = (message.text or "").strip()
    data = await state.get_data()
    labels = data.get("ordinal_labels")
    if not label or "\n" in label or not isinstance(labels, list):
        await _render_ordinal_draft(
            message,
            state,
            update_main_message,
            error=TEXTS[TextKey.INVALID_FIELD_INPUT],
        )
        return
    await state.update_data(ordinal_labels=[*labels, label])
    await _render_ordinal_draft(message, state, update_main_message)


@router.callback_query(OrdinalDraftCallback.filter())
async def edit_ordinal_draft(
    query: CallbackQueryWithMessage,
    callback_data: OrdinalDraftCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Modify or commit the staged ordinal option list."""
    data = await state.get_data()
    labels = data.get("ordinal_labels")
    if not isinstance(labels, list) or not all(
        isinstance(label, str) for label in labels
    ):
        await _invalid_form(state, query, update_main_message)
        return
    if callback_data.action is OrdinalDraftAction.ADD:
        await query.answer()
        await _render_ordinal_draft(query, state, update_main_message, adding=True)
        return
    if callback_data.action is OrdinalDraftAction.REMOVE:
        await state.update_data(ordinal_labels=labels[:-1])
        await query.answer()
        await _render_ordinal_draft(query, state, update_main_message)
        return
    if callback_data.action is OrdinalDraftAction.RESET:
        await state.update_data(ordinal_labels=[])
        await query.answer()
        await _render_ordinal_draft(query, state, update_main_message)
        return
    start = data.get("ordinal_start")
    if len(labels) < 2 or start not in (0, 1):
        await query.answer(TEXTS[TextKey.INVALID_FIELD_INPUT], show_alert=True)
        return
    config = OrdinalConfig(
        tuple(OrdinalOption(start + index, label) for index, label in enumerate(labels))
    )
    await query.answer()
    await _save_config(query, state, telegram_id, services, update_main_message, config)


@router.message(FieldForm.waiting_emoji, F.text)
async def save_emoji(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a non-empty emoji string as a display-only setting."""
    field_id = _field_id(await state.get_data())
    if field_id is None or not (emoji := (message.text or "").strip()):
        await _invalid_form(state, message, update_main_message)
        return
    await _update_display(
        message,
        state,
        telegram_id,
        field_id,
        services,
        update_main_message,
        emoji=emoji,
        update_emoji=True,
    )


@router.message(FieldForm.waiting_palette, F.text)
async def save_palette(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a validated three-color palette for the core state field."""
    field_id = _field_id(await state.get_data())
    try:
        minimum, middle, maximum = (message.text or "").split()
        palette = StatePalette(minimum, middle, maximum)
    except TypeError, ValueError, InvalidFieldVersion:
        await _show_input_error(
            state,
            message,
            update_main_message,
            TEXTS[TextKey.INVALID_PALETTE_INPUT],
            TEXTS[TextKey.PALETTE_PROMPT],
        )
        return
    if field_id is None:
        await _invalid_form(state, message, update_main_message)
        return
    await _update_display(
        message,
        state,
        telegram_id,
        field_id,
        services,
        update_main_message,
        state_palette=palette,
        update_palette=True,
    )


async def _save_config(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
    config: ScaleConfig | OrdinalConfig,
) -> None:
    data = await state.get_data()
    profile = await _profile(telegram_id, services)
    if profile is None or not isinstance(data.get("mode"), str):
        await _invalid_form(state, event, update_main_message)
        return
    if data["mode"] == "create" and isinstance(data.get("name"), str):
        await _create_field(profile, data["name"], config, services)
        await state.clear()
        await _render_fields(event, state, profile, services, update_main_message)
        return
    if data["mode"] == "version" and (field_id := _field_id(data)) is not None:
        try:
            field = await services.add_field_version().execute(
                AddFieldVersion(profile.id, field_id, config)
            )
        except FieldNotFound, InvalidFieldVersion:
            await _invalid_form(state, event, update_main_message)
            return
        await state.clear()
        await _render_field(event, state, field, update_main_message)
        return
    await _invalid_form(state, event, update_main_message)


async def _create_field(
    profile: UserProfile,
    name: str,
    config: ScaleConfig | OrdinalConfig | TextConfig,
    services: ApplicationServices,
) -> Field:
    fields = await services.list_fields().execute(ListFields(profile.id))
    return await services.create_field().execute(
        CreateField(
            profile.id,
            name,
            config,
            FieldDisplayConfig(),
            sort_order=max((field.sort_order for field in fields), default=-1) + 1,
        )
    )


async def _update_display(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    telegram_id: int,
    field_id: UUID,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
    *,
    emoji: str | None = None,
    update_emoji: bool = False,
    show_in_calendar: bool | None = None,
    state_palette: StatePalette | None = None,
    update_palette: bool = False,
) -> None:
    profile = await _profile(telegram_id, services)
    if profile is None:
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        else:
            await _invalid_form(state, event, update_main_message)
        return
    field = await _field(profile, field_id, services)
    if field is None:
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        else:
            await _invalid_form(state, event, update_main_message)
        return
    if update_palette and not field.is_core:
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        else:
            await _invalid_form(state, event, update_main_message)
        return
    display = field.display_config
    try:
        updated = await services.set_field_display().execute(
            SetFieldDisplay(
                profile.id,
                field.id,
                FieldDisplayConfig(
                    emoji=emoji if update_emoji else display.emoji,
                    show_in_calendar=(
                        display.show_in_calendar
                        if show_in_calendar is None
                        else show_in_calendar
                    ),
                    state_palette=(
                        display.state_palette if not update_palette else state_palette
                    ),
                ),
            )
        )
    except FieldNotFound, InvalidFieldVersion:
        await _invalid_form(state, event, update_main_message)
        return
    await state.clear()
    if isinstance(event, CallbackQueryWithMessage):
        await event.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await _render_field(event, state, updated, update_main_message)


async def _render_ordinal_draft(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    update_main_message: UpdateMainMessage,
    *,
    adding: bool = False,
    error: str | None = None,
) -> None:
    data = await state.get_data()
    labels = data.get("ordinal_labels")
    if not isinstance(labels, list) or not all(
        isinstance(label, str) for label in labels
    ):
        await _invalid_form(state, event, update_main_message)
        return
    options = (
        "\n".join(
            f"{index}. {escape(label)}" for index, label in enumerate(labels, start=1)
        )
        or "—"
    )
    prompt = (
        TEXTS[TextKey.ORDINAL_NEXT_PROMPT]
        if labels or adding
        else TEXTS[TextKey.ORDINAL_FIRST_PROMPT]
    )
    draft = TEXTS[TextKey.ORDINAL_DRAFT].format(options=options)
    parts = [part for part in (error, draft, prompt) if part]
    await update_main_message(
        state,
        event,
        "\n\n".join(parts),
        reply_markup=ordinal_draft_keyboard(len(labels)),
    )


async def _show_input_error(
    state: FSMContext,
    event: Message | CallbackQueryWithMessage,
    update_main_message: UpdateMainMessage,
    error: str,
    prompt: str,
) -> None:
    await update_main_message(state, event, f"{error}\n\n{prompt}")


async def _render_order(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    fields: tuple[Field, ...],
    selected_id: UUID | None,
    update_main_message: UpdateMainMessage,
) -> None:
    await update_main_message(
        state,
        event,
        TEXTS[TextKey.FIELD_ORDER_TITLE],
        reply_markup=field_order_keyboard(fields, selected_id),
    )


async def _render_palette_selector(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    field: Field,
    palette: StatePalette,
    update_main_message: UpdateMainMessage,
) -> None:
    config = field.current_version.config
    if not isinstance(config, ScaleConfig):
        return
    await update_main_message(
        state,
        event,
        format_palette_message(config, palette),
        reply_markup=palette_keyboard(field.id),
    )


async def _render_fields(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    profile: UserProfile,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    fields = await services.list_fields().execute(ListFields(profile.id))
    await update_main_message(
        state,
        event,
        format_fields_list(fields),
        reply_markup=fields_keyboard(fields),
    )


async def _render_field(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    field: Field,
    update_main_message: UpdateMainMessage,
) -> None:
    await update_main_message(
        state,
        event,
        format_field_card(field),
        reply_markup=field_card_keyboard(field),
    )


async def _profile(
    telegram_id: int, services: ApplicationServices
) -> UserProfile | None:
    return await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )


async def _field(
    profile: UserProfile, field_id: UUID, services: ApplicationServices
) -> Field | None:
    return next(
        (
            field
            for field in await services.list_fields().execute(ListFields(profile.id))
            if field.id == field_id
        ),
        None,
    )


def _field_id(data: dict[str, object]) -> UUID | None:
    value = data.get("field_id")
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


async def _invalid_form(
    state: FSMContext,
    event: Message | CallbackQueryWithMessage,
    update_main_message: UpdateMainMessage,
) -> None:
    await state.clear()
    await update_main_message(state, event, TEXTS[TextKey.INVALID_FIELD_INPUT])

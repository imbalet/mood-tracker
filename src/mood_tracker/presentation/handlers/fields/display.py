"""Display settings: lifecycle, emoji, calendar visibility and palettes."""

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.contracts.questionnaires import (
    DeleteField,
    DetachFieldFromQuestionnaire,
    ListQuestionnaireFields,
    SetFieldDisplay,
    SetQuestionnaireFieldEnabled,
    SetQuestionnaireFieldRequired,
)
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.domain.entities import FieldDisplayConfig, StatePalette
from mood_tracker.domain.errors import (
    CoreFieldViolation,
    InvalidFieldVersion,
    QuestionnaireViolation,
)
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    PaletteCallback,
    PalettePreset,
    QuestionnaireFieldAction,
    QuestionnaireFieldCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.handlers.fields.common import (
    invalidate_form,
    render_field,
    render_fields,
    render_palette,
    show_input_error,
)
from mood_tracker.presentation.palettes import PALETTES
from mood_tracker.presentation.queries import get_owned_field, get_user_profile
from mood_tracker.presentation.screens.screen import Screen
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import (
    FieldDisplayChange,
    FieldDisplayData,
    InvalidPresentationData,
    PresentationData,
)
from mood_tracker.presentation.utils import KeyboardBuilder, UpdateMainMessage
from mood_tracker.presentation.view_models import make_palette_view

router = Router(name="fields_display")


@router.callback_query(FieldCallback.filter(F.action == FieldAction.EMOJI))
async def prompt_emoji(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Ask for a replacement emoji."""
    await state.set_state(FieldDisplayChange.waiting_emoji)
    await presentation_data.write(FieldDisplayData(callback_data.field_id))
    await query.answer()
    await update_main_message(presentation_data, query, TEXTS[TextKey.EMOJI_PROMPT])


@router.callback_query(FieldCallback.filter(F.action == FieldAction.CLEAR_EMOJI))
async def clear_emoji(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Remove the global emoji while retaining other visual settings."""
    await _update_display(
        query,
        state,
        presentation_data,
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
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Toggle whether a field is offered to calendar renderers."""
    profile = await get_user_profile(telegram_id, services)
    field = (
        await get_owned_field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    if field is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await _update_display(
        query,
        state,
        presentation_data,
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
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Show visual palette presets and the custom color route."""
    profile = await get_user_profile(telegram_id, services)
    field = (
        await get_owned_field(profile, callback_data.field_id, services)
        if profile is not None
        else None
    )
    view = make_palette_view(field) if field is not None else None
    if view is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_palette(query, presentation_data, view, update_main_message)


@router.callback_query(PaletteCallback.filter())
async def save_palette_preset(
    query: CallbackQueryWithMessage,
    callback_data: PaletteCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Apply a preset or request exactly three custom HEX colors."""
    if callback_data.preset is PalettePreset.CUSTOM:
        await state.set_state(FieldDisplayChange.waiting_palette)
        await presentation_data.write(FieldDisplayData(callback_data.field_id))
        await query.answer()
        await update_main_message(
            presentation_data, query, TEXTS[TextKey.PALETTE_PROMPT]
        )
        return
    await _update_display(
        query,
        state,
        presentation_data,
        telegram_id,
        callback_data.field_id,
        services,
        update_main_message,
        state_palette=PALETTES[callback_data.preset],
        update_palette=True,
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.DELETE))
async def delete_confirmation(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Ask the user to confirm a global soft-delete."""
    builder = KeyboardBuilder()
    builder.row_buttons_tuple(
        (
            TextKey.FIELD_DELETE_CONFIRM,
            FieldCallback(
                action=FieldAction.CONFIRM_DELETE,
                field_id=callback_data.field_id,
                kind=callback_data.kind,
            ),
        )
    )
    builder.row_buttons_tuple(
        (
            TextKey.BACK,
            FieldCallback(
                action=FieldAction.OPEN,
                field_id=callback_data.field_id,
                kind=callback_data.kind,
            ),
        )
    )
    await update_main_message(
        presentation_data,
        query,
        Screen(TEXTS[TextKey.FIELD_DELETE_PROMPT], builder.as_markup()),
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.CONFIRM_DELETE))
async def delete_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Soft-delete one ordinary field after confirmation."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    try:
        await services.delete_field().execute(
            DeleteField(profile.id, callback_data.field_id)
        )
    except FieldNotFound, CoreFieldViolation, QuestionnaireViolation:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await render_fields(
        query,
        presentation_data,
        profile,
        services,
        update_main_message,
        callback_data.kind,
    )


@router.callback_query(QuestionnaireFieldCallback.filter())
async def change_questionnaire_placement(
    query: CallbackQueryWithMessage,
    callback_data: QuestionnaireFieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    try:
        if callback_data.action is QuestionnaireFieldAction.TOGGLE_REQUIRED:
            # Read the current placement from the explicit questionnaire.
            items = await services.list_questionnaire_fields().execute(
                ListQuestionnaireFields(profile.id, callback_data.kind)
            )
            item = next(
                (item for item in items if item.field.id == callback_data.field_id),
                None,
            )
            if item is None:
                raise FieldNotFound
            field = await services.set_questionnaire_field_required().execute(
                SetQuestionnaireFieldRequired(
                    profile.id,
                    callback_data.field_id,
                    callback_data.kind,
                    not item.placement.is_required,
                )
            )
        elif callback_data.action in (
            QuestionnaireFieldAction.ENABLE,
            QuestionnaireFieldAction.DISABLE,
        ):
            field = await services.set_questionnaire_field_enabled().execute(
                SetQuestionnaireFieldEnabled(
                    profile.id,
                    callback_data.field_id,
                    callback_data.kind,
                    callback_data.action is QuestionnaireFieldAction.ENABLE,
                )
            )
        else:
            field = await services.detach_field_from_questionnaire().execute(
                DetachFieldFromQuestionnaire(
                    profile.id, callback_data.field_id, callback_data.kind
                )
            )
    except (
        FieldNotFound,
        CoreFieldViolation,
        InvalidFieldVersion,
        QuestionnaireViolation,
    ):
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    if callback_data.action is QuestionnaireFieldAction.DETACH:
        await render_fields(
            query,
            presentation_data,
            profile,
            services,
            update_main_message,
            callback_data.kind,
        )
        return
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, callback_data.kind)
    )
    item = next((item for item in items if item.field.id == field.id), None)
    if item is None:
        return
    await render_field(
        query,
        presentation_data,
        field,
        update_main_message,
        item.placement,
        callback_data.kind,
    )


@router.message(FieldDisplayChange.waiting_emoji, F.text)
async def save_emoji(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a non-empty emoji string as a display-only setting."""
    try:
        form = await presentation_data.require(FieldDisplayData)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    if not (emoji := (message.text or "").strip()):
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    await _update_display(
        message,
        state,
        presentation_data,
        telegram_id,
        form.field_id,
        services,
        update_main_message,
        emoji=emoji,
        update_emoji=True,
    )


@router.message(FieldDisplayChange.waiting_palette, F.text)
async def save_palette(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a validated three-color palette for the core state field."""
    try:
        form = await presentation_data.require(FieldDisplayData)
    except InvalidPresentationData:
        await invalidate_form(state, presentation_data, message, update_main_message)
        return
    try:
        minimum, middle, maximum = (message.text or "").split()
        palette = StatePalette(minimum, middle, maximum)
    except TypeError, ValueError, InvalidFieldVersion:
        await show_input_error(
            presentation_data,
            message,
            update_main_message,
            TEXTS[TextKey.INVALID_PALETTE_INPUT],
            TEXTS[TextKey.PALETTE_PROMPT],
        )
        return
    await _update_display(
        message,
        state,
        presentation_data,
        telegram_id,
        form.field_id,
        services,
        update_main_message,
        state_palette=palette,
        update_palette=True,
    )


async def _update_display(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
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
    """Replace one owned field's display configuration."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        else:
            await invalidate_form(state, presentation_data, event, update_main_message)
        return
    field = await get_owned_field(profile, field_id, services)
    if field is None:
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        else:
            await invalidate_form(state, presentation_data, event, update_main_message)
        return
    if update_palette and (field.display_config.state_palette is None):
        if isinstance(event, CallbackQueryWithMessage):
            await event.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        else:
            await invalidate_form(state, presentation_data, event, update_main_message)
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
        await invalidate_form(state, presentation_data, event, update_main_message)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    if isinstance(event, CallbackQueryWithMessage):
        await event.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await render_field(event, presentation_data, updated, update_main_message)

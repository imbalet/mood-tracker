"""Field-list navigation and entry points into management flows."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from mood_tracker.application.commands import ListQuestionnaireFields
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldsListAction,
    FieldsListCallback,
    MenuCallback,
    MenuSection,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.handlers.fields.common import (
    render_field,
    render_fields,
    render_order,
)
from mood_tracker.presentation.keyboards import field_type_keyboard
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="fields_overview")


@router.callback_query(MenuCallback.filter(F.section == MenuSection.FIELDS))
async def open_fields(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open all field settings owned by the current Telegram user."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await render_fields(
        query, presentation_data, profile, services, update_main_message
    )


@router.callback_query(FieldsListCallback.filter(F.action == FieldsListAction.CREATE))
async def choose_field_type(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Show semantic-type choices for a new custom field."""
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await update_main_message(
        presentation_data,
        query,
        TEXTS[TextKey.CREATE_FIELD_TYPE],
        reply_markup=field_type_keyboard(),
    )


@router.callback_query(FieldsListCallback.filter(F.action == FieldsListAction.ORDER))
async def open_order_from_fields(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the order editor before a field has been selected."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, QuestionnaireKind.DAY)
    )
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await render_order(
        query,
        presentation_data,
        tuple(item.field for item in items),
        None,
        update_main_message,
    )


@router.callback_query(FieldCallback.filter(F.action == FieldAction.OPEN))
async def open_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open a field card after resolving it within the current owner scope."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, QuestionnaireKind.DAY)
    )
    item = next(
        (item for item in items if item.field.id == callback_data.field_id), None
    )
    if item is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await render_field(
        query, presentation_data, item.field, update_main_message, item.placement
    )

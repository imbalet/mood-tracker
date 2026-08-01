"""Inline field-order editing."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from mood_tracker.application.commands import (
    ListQuestionnaireFields,
    MoveQuestionnaireField,
)
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    FieldAction,
    FieldCallback,
    FieldMoveCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.handlers.fields.common import render_order
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="fields_ordering")


@router.callback_query(FieldCallback.filter(F.action == FieldAction.ORDER))
async def open_field_order(
    query: CallbackQueryWithMessage,
    callback_data: FieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open an inline list where a selected field moves in place."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, callback_data.kind)
    )
    fields = tuple(item.field for item in items)
    if not any(field.id == callback_data.field_id for field in fields):
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await query.answer()
    await render_order(
        query,
        presentation_data,
        fields,
        callback_data.field_id,
        update_main_message,
        callback_data.kind,
    )


@router.callback_query(FieldMoveCallback.filter())
async def move_field(
    query: CallbackQueryWithMessage,
    callback_data: FieldMoveCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Move one field without creating ambiguous duplicate positions."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, callback_data.kind)
    )
    current_fields = tuple(item.field for item in items)
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
        items = await services.questionnaire_field().move(
            MoveQuestionnaireField(
                profile.id,
                callback_data.field_id,
                callback_data.kind,
                callback_data.direction,
            )
        )
    except FieldNotFound:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await query.answer(TEXTS[TextKey.FIELD_CONFIG_SAVED])
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_order(
        query,
        presentation_data,
        tuple(item.field for item in items),
        callback_data.field_id,
        update_main_message,
        callback_data.kind,
    )

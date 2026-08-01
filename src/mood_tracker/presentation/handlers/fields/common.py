"""Shared owner-scoped lookups and screen rendering for field handlers."""

from uuid import UUID

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import ListQuestionnaireFields
from mood_tracker.domain.entities import Field, UserProfile
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens import (
    field_card_screen,
    field_order_screen,
    fields_list_screen,
    palette_screen,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.view_models import (
    PaletteView,
    make_field_card_view,
    make_field_order_view,
    make_fields_list_view,
)


async def render_fields(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    profile: UserProfile,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
    kind: QuestionnaireKind = QuestionnaireKind.DAY,
) -> None:
    """Render the field settings list for an owned profile."""
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, kind)
    )
    await update_main_message(
        presentation_data,
        event,
        fields_list_screen(
            make_fields_list_view(tuple(item.field for item in items), kind)
        ),
    )


async def render_field(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    field: Field,
    update_main_message: UpdateMainMessage,
    placement: QuestionnaireField | None = None,
    kind: QuestionnaireKind = QuestionnaireKind.DAY,
) -> None:
    """Render one field's settings card."""
    await update_main_message(
        presentation_data,
        event,
        field_card_screen(make_field_card_view(field, placement, kind)),
    )


async def render_order(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    fields: tuple[Field, ...],
    selected_id: UUID | None,
    update_main_message: UpdateMainMessage,
    kind: QuestionnaireKind = QuestionnaireKind.DAY,
) -> None:
    """Render the selected-field order editor."""
    await update_main_message(
        presentation_data,
        event,
        field_order_screen(make_field_order_view(fields, selected_id, kind)),
    )


async def render_palette(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    view: PaletteView,
    update_main_message: UpdateMainMessage,
) -> None:
    """Render the rich state-palette selector."""
    await update_main_message(presentation_data, event, palette_screen(view))


async def show_input_error(
    presentation_data: PresentationData,
    event: Message | CallbackQueryWithMessage,
    update_main_message: UpdateMainMessage,
    error: str,
    prompt: str,
) -> None:
    """Keep an input flow open while explaining a validation failure."""
    await update_main_message(presentation_data, event, f"{error}\n\n{prompt}")


async def invalidate_form(
    state: FSMContext,
    presentation_data: PresentationData,
    event: Message | CallbackQueryWithMessage,
    update_main_message: UpdateMainMessage,
) -> None:
    """Clear corrupt FSM data and show a recoverable error."""
    await state.set_state(None)
    await presentation_data.clear_flow()
    await update_main_message(
        presentation_data, event, TEXTS[TextKey.INVALID_FIELD_INPUT]
    )

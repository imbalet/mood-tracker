"""Fast event capture command."""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import CreateQuickEvent
from mood_tracker.domain.errors import InvalidFieldValue
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage

router = Router(name="events")


@router.message(Command("event"))
async def capture_event(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Capture `/event <text>` as a durable event draft without a form flow."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.START_FIRST]
        )
        return
    text = (command.args or "").strip()
    if not text:
        await update_main_message(
            presentation_data,
            message,
            TEXTS[TextKey.EVENT_COMMAND_HINT],
        )
        return
    try:
        await services.create_quick_event().execute(CreateQuickEvent(profile.id, text))
    except InvalidFieldValue:
        await update_main_message(
            presentation_data, message, TEXTS[TextKey.EVENT_NOT_SAVED]
        )
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await update_main_message(
        presentation_data, message, TEXTS[TextKey.EVENT_SAVED], create_new=True
    )

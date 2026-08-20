"""Fast capture and a questionnaire flow for events."""

from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.contracts.events import (
    ChangeEventTime,
    CompleteEvent,
    CreateEvent,
    CreateQuickEvent,
    DeleteEvent,
    GetEvent,
    SaveEventValue,
    SkipEventField,
)
from mood_tracker.application.contracts.questionnaires import ListQuestionnaireFields
from mood_tracker.application.errors import FieldNotFound
from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig, UserProfile
from mood_tracker.domain.enums import QuestionnaireKind
from mood_tracker.domain.errors import IncompleteDay, InvalidFieldValue
from mood_tracker.presentation.callbacks.callbacks import (
    EventAction,
    EventCallback,
    EventTimeCallback,
    EventValueCallback,
    SkipEventFieldCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.screens.events import (
    AskTimeScreen,
    ChangeTimeScreen,
    ChooseEventCompleteScreen,
    DeleteEventConfirmScreen,
    EventEmptyScreen,
    EventScreen,
    InvalidTimeScreen,
    NonEmptyTextRequiredScreen,
    PromptTextScreen,
    PromptValueScreen,
    SendTextScreen,
    SetTimeScreen,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import EventFlow, EventInputData, PresentationData
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage

router = Router(name="events")
EventSource = Message | CallbackQueryWithMessage


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
    """Create a quick draft or start today's complete questionnaire."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        # TODO: move to middleware
        await update_main_message(TEXTS[TextKey.START_FIRST])
        return
    text = (command.args or "").strip()
    if text:
        try:
            created = await services.create_quick_event().execute(
                CreateQuickEvent(profile.id, text)
            )
        except InvalidFieldValue:
            await update_main_message(TEXTS[TextKey.EVENT_NOT_SAVED])
            return
        await _render_event(
            message,
            presentation_data,
            profile,
            created.id,
            services,
            update_main_message,
        )
        return
    await update_main_message(ChooseEventCompleteScreen(date=_today(profile)))


@router.callback_query(EventCallback.filter(F.action == EventAction.START))
async def start_event_from_day(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None or callback_data.day is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    day = _parse_day(callback_data.day)
    await update_main_message(
        AskTimeScreen(allow_now=day == _today(profile), day_date=day)
    )


@router.callback_query(EventCallback.filter(F.action == EventAction.QUICK_TEXT))
async def quick_text_prompt(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        return
    await state.set_state(EventFlow.waiting_text)
    await presentation_data.write(EventInputData(None, _today(profile)))
    await update_main_message(SendTextScreen())


@router.callback_query(EventCallback.filter(F.action == EventAction.CONTINUE))
async def continue_event(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None or callback_data.event_id is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await _prompt_next(
        query,
        state,
        presentation_data,
        profile,
        callback_data.event_id,
        services,
        update_main_message,
    )


@router.callback_query(EventCallback.filter(F.action == EventAction.OPEN))
async def open_event(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None or callback_data.event_id is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await _render_event(
        query,
        presentation_data,
        profile,
        callback_data.event_id,
        services,
        update_main_message,
    )


@router.callback_query(EventCallback.filter(F.action == EventAction.CHANGE_TIME))
async def change_time_prompt(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None or callback_data.event_id is None:
        return
    current = await services.get_event().execute(
        GetEvent(profile.id, callback_data.event_id)
    )
    day_date = current.occurred_at.astimezone(
        ZoneInfo(current.occurred_timezone.name)
    ).date()
    await state.set_state(EventFlow.waiting_time)
    await presentation_data.write(EventInputData(current.id, day_date))
    await update_main_message(ChangeTimeScreen())


@router.callback_query(EventCallback.filter(F.action == EventAction.DELETE))
async def delete_confirmation(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    if callback_data.event_id is None:
        return
    await update_main_message(DeleteEventConfirmScreen(event_id=callback_data.event_id))


@router.callback_query(EventCallback.filter(F.action == EventAction.CONFIRM_DELETE))
async def delete_event(
    query: CallbackQueryWithMessage,
    callback_data: EventCallback,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None or callback_data.event_id is None:
        return
    await services.delete_event().execute(
        DeleteEvent(profile.id, callback_data.event_id)
    )
    # TODO: make day screen with notice
    await update_main_message("Событие удалено.")


@router.callback_query(EventTimeCallback.filter())
async def choose_time(
    query: CallbackQueryWithMessage,
    callback_data: EventTimeCallback,
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
    day_date = _parse_day(callback_data.day)
    if not callback_data.now:
        await state.set_state(EventFlow.waiting_time)
        await presentation_data.write(EventInputData(None, day_date))
        await update_main_message(SetTimeScreen())
        return
    current_time = datetime.now(UTC).astimezone(ZoneInfo(profile.timezone.name)).time()
    await _create_and_prompt(
        query,
        state,
        presentation_data,
        profile,
        day_date,
        current_time,
        services,
        update_main_message,
    )


@router.message(EventFlow.waiting_time, F.text)
async def enter_time(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    data = await presentation_data.require(EventInputData)
    try:
        selected = time.fromisoformat((message.text or "").strip())
        if profile is None or selected.second or selected.tzinfo is not None:
            raise ValueError
    except ValueError:
        await update_main_message(InvalidTimeScreen())
        return
    if data.event_id is not None:
        current = await services.get_event().execute(
            GetEvent(profile.id, data.event_id)
        )
        changed_at = datetime.combine(
            data.day_date, selected, ZoneInfo(current.occurred_timezone.name)
        ).astimezone(UTC)
        await services.change_event_time().execute(
            ChangeEventTime(profile.id, data.event_id, changed_at)
        )
        await _render_event(
            message,
            presentation_data,
            profile,
            data.event_id,
            services,
            update_main_message,
        )
        return
    await _create_and_prompt(
        message,
        state,
        presentation_data,
        profile,
        data.day_date,
        selected,
        services,
        update_main_message,
    )


async def _create_and_prompt(
    event: EventSource,
    state: FSMContext,
    presentation_data: PresentationData,
    profile: UserProfile,
    day_date: date,
    selected_time: time,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    occurred_at = datetime.combine(
        day_date, selected_time, ZoneInfo(profile.timezone.name)
    ).astimezone(UTC)
    created = await services.create_event().execute(
        CreateEvent(profile.id, occurred_at, profile.timezone)
    )
    await _prompt_next(
        event,
        state,
        presentation_data,
        profile,
        created.id,
        services,
        update_main_message,
    )


async def _prompt_next(
    event: EventSource,
    state: FSMContext,
    presentation_data: PresentationData,
    profile: UserProfile,
    event_id: UUID,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    current = await services.get_event().execute(GetEvent(profile.id, event_id))
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, QuestionnaireKind.EVENT)
    )
    item = next(
        (
            candidate
            for candidate in items
            if candidate.placement.is_enabled
            and not current.has_completed_step(candidate.field.id)
        ),
        None,
    )
    if item is None:
        try:
            completed = await services.complete_event().execute(
                CompleteEvent(profile.id, event_id)
            )
        except IncompleteDay:
            # This can only happen after a questionnaire changes mid-flow.
            await _render_event(
                event,
                presentation_data,
                profile,
                event_id,
                services,
                update_main_message,
            )
            return
        if completed.deleted_at is not None:
            await update_main_message(EventEmptyScreen())
            return
        await _render_event(
            event,
            presentation_data,
            profile,
            event_id,
            services,
            update_main_message,
        )
        return
    config = item.field.current_version.config
    if not isinstance(config, (ScaleConfig, OrdinalConfig)):
        # TODO сделать нормально условие на текст
        await state.set_state(EventFlow.waiting_text)
        await presentation_data.write(
            EventInputData(event_id, current.occurred_at.date(), item.field.id)
        )
        await update_main_message(PromptTextScreen(item=item, event_id=event_id))
        return
    await update_main_message(PromptValueScreen(item=item, event_id=event_id))


@router.callback_query(EventValueCallback.filter())
async def save_value(
    query: CallbackQueryWithMessage,
    callback_data: EventValueCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        return
    try:
        await services.save_event_value().execute(
            SaveEventValue(
                profile.id,
                callback_data.event_id,
                callback_data.field_id,
                callback_data.value,
            )
        )
    except FieldNotFound, InvalidFieldValue:
        await query.answer(TEXTS[TextKey.FIELD_VALUE_UNAVAILABLE], show_alert=True)
        return
    await _prompt_next(
        query,
        state,
        presentation_data,
        profile,
        callback_data.event_id,
        services,
        update_main_message,
    )


@router.callback_query(SkipEventFieldCallback.filter())
async def skip_value(
    query: CallbackQueryWithMessage,
    callback_data: SkipEventFieldCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        return
    await services.skip_event_field().execute(
        SkipEventField(profile.id, callback_data.event_id, callback_data.field_id)
    )
    await _prompt_next(
        query,
        state,
        presentation_data,
        profile,
        callback_data.event_id,
        services,
        update_main_message,
    )


@router.message(EventFlow.waiting_text, F.text)
async def save_text(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    profile = await get_user_profile(telegram_id, services)
    data = await presentation_data.require(EventInputData)
    if profile is None:
        return
    if data.event_id is None:
        try:
            created = await services.create_quick_event().execute(
                CreateQuickEvent(profile.id, message.text or "")
            )
        except InvalidFieldValue:
            await update_main_message(NonEmptyTextRequiredScreen())
            return
        await _render_event(
            message,
            presentation_data,
            profile,
            created.id,
            services,
            update_main_message,
        )
        return
    if data.field_id is None:
        return
    try:
        await services.save_event_value().execute(
            SaveEventValue(profile.id, data.event_id, data.field_id, message.text or "")
        )
    except InvalidFieldValue:
        await update_main_message(NonEmptyTextRequiredScreen())
        return
    await _prompt_next(
        message,
        state,
        presentation_data,
        profile,
        data.event_id,
        services,
        update_main_message,
    )


async def _render_event(
    event: EventSource,
    presentation_data: PresentationData,
    profile: UserProfile,
    event_id: UUID,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    current = await services.get_event().execute(GetEvent(profile.id, event_id))
    local = current.occurred_at.astimezone(ZoneInfo(current.occurred_timezone.name))
    items = await services.list_questionnaire_fields().execute(
        ListQuestionnaireFields(profile.id, QuestionnaireKind.EVENT)
    )
    # TODO: rename
    await update_main_message(
        EventScreen(local=local, current=current, items=items, profile=profile)
    )


def _today(profile: UserProfile) -> date:
    return datetime.now(UTC).astimezone(ZoneInfo(profile.timezone.name)).date()


def _parse_day(value: str) -> date:
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def _render_value(field: Field, value: int | str, version_id: UUID) -> str:
    version = field.get_version(version_id)
    if version is None:
        return str(value)
    config = version.config
    if isinstance(config, OrdinalConfig) and isinstance(value, int):
        return next(
            (option.label for option in config.options if option.value == value),
            str(value),
        )
    if isinstance(config, ScaleConfig):
        return f"{value}/{config.maximum}"
    return str(value)

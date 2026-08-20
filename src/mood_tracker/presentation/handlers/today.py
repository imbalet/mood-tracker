"""Handlers for filling, resuming and editing a daily entry."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.contracts.diary import (
    ConfirmReference,
    DayForm,
    GetDay,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.contracts.events import GetEventsForDate
from mood_tracker.application.errors import DayNotFound, FieldNotFound
from mood_tracker.domain.entities import Field, UserProfile
from mood_tracker.domain.errors import InvalidFieldValue
from mood_tracker.presentation.callbacks.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    MenuCallback,
    MenuSection,
    OpenDayCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.errors import StaleCallback
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.screens.day import (
    DayCardScreen,
    DayPromptKind,
    DayValuePromptScreen,
    ReferenceReviewScreen,
    make_day_value_prompt_view,
    make_reference_review_view,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import (
    Diary,
    DiaryTextData,
    InvalidPresentationData,
    PresentationData,
)
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.utils.callback_query import CallbackQueryWithMessage

router = Router(name="today")


@router.callback_query(MenuCallback.filter(F.section == MenuSection.TODAY))
@router.message(Command("today"))
async def open_today_from_menu(
    event: Message | CallbackQueryWithMessage,
    *,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    # TODO: maybe move user profile check to middleware
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await update_main_message(TEXTS[TextKey.START_FIRST])
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_day(
        event,
        presentation_data,
        profile,
        _today(profile),
        services,
        update_main_message,
    )


@router.callback_query(DayValueCallback.filter())
async def save_value(
    query: CallbackQueryWithMessage,
    callback_data: DayValueCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a Scale or Ordinal answer selected from an inline keyboard."""
    profile, day_date = await _get_day_context(callback_data.day, telegram_id, services)
    try:
        review = await services.save_day_value().execute(
            SaveDayValue(
                profile.id, day_date, callback_data.field_id, callback_data.value
            )
        )
    # TODO: move to exception handler
    except FieldNotFound, InvalidFieldValue:
        await query.answer(TEXTS[TextKey.FIELD_VALUE_UNAVAILABLE], show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    if review is not None:
        await update_main_message(
            ReferenceReviewScreen(make_reference_review_view(review)),
        )
    else:
        await render_day(
            query, presentation_data, profile, day_date, services, update_main_message
        )


@router.callback_query(OpenDayCallback.filter())
async def open_day_card(
    query: CallbackQueryWithMessage,
    callback_data: OpenDayCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Return from an answer prompt to the selected day summary."""
    profile, day_date = await _get_day_context(callback_data.day, telegram_id, services)
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_day(
        query, presentation_data, profile, day_date, services, update_main_message
    )


@router.callback_query(SkipTextCallback.filter())
async def skip_text(
    query: CallbackQueryWithMessage,
    callback_data: SkipTextCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist an explicit Text skip."""
    profile, day_date = await _get_day_context(callback_data.day, telegram_id, services)
    await services.skip_day_text().execute(
        SkipDayText(profile.id, day_date, callback_data.field_id)
    )
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_day(
        query, presentation_data, profile, day_date, services, update_main_message
    )


@router.callback_query(ReferenceCallback.filter())
async def confirm_reference(
    query: CallbackQueryWithMessage,
    callback_data: ReferenceCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist the answer to a candidate best/worst reference day."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    try:
        await services.confirm_reference().execute(
            ConfirmReference(
                profile.id,
                callback_data.day_id,
                callback_data.type,
                callback_data.is_new_record,
            )
        )
    except DayNotFound:
        await query.answer(TEXTS[TextKey.DAY_UNAVAILABLE], show_alert=True)
        return
    await query.answer()
    await render_day(
        query,
        presentation_data,
        profile,
        _today(profile),
        services,
        update_main_message,
    )


@router.callback_query(EditDayValueCallback.filter())
async def edit_value(
    query: CallbackQueryWithMessage,
    callback_data: EditDayValueCallback,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Prompt a field of an existing day for a replacement value."""
    profile, day_date = await _get_day_context(callback_data.day, telegram_id, services)
    form = await services.get_day().execute(GetDay(profile.id, day_date))
    field = next(
        (item for item in form.fields if item.id == callback_data.field_id), None
    )
    if field is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await query.answer()
    await _prompt_field(
        query, state, presentation_data, form, field, update_main_message
    )


@router.message(Diary.waiting_text, F.text)
async def save_text(
    message: Message,
    state: FSMContext,
    presentation_data: PresentationData,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist text supplied for the pending Text field."""
    profile = await get_user_profile(telegram_id, services)
    try:
        form_data = await presentation_data.require(DiaryTextData)
    except InvalidPresentationData:
        await _reset_text_flow(state, presentation_data, message, update_main_message)
        return
    if profile is None:
        await _reset_text_flow(state, presentation_data, message, update_main_message)
        return
    try:
        await services.save_day_value().execute(
            SaveDayValue(
                profile.id, form_data.day_date, form_data.field_id, message.text or ""
            )
        )
    except FieldNotFound, InvalidFieldValue:
        await _reset_text_flow(
            state,
            presentation_data,
            message,
            update_main_message,
            text_key=TextKey.TEXT_SAVE_FAILED,
        )
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    await render_day(
        message,
        presentation_data,
        profile,
        form_data.day_date,
        services,
        update_main_message,
    )


async def _reset_text_flow(
    state: FSMContext,
    presentation_data: PresentationData,
    message: Message,
    update_main_message: UpdateMainMessage,
    *,
    text_key: TextKey = TextKey.OPEN_TODAY_AGAIN,
) -> None:
    """Discard an unrecoverable Text-input flow and explain how to restart it."""
    await state.set_state(None)
    await presentation_data.clear_flow()
    await update_main_message(TEXTS[text_key])


async def _get_day_context(
    encoded_day: str,
    telegram_id: int,
    services: ApplicationServices,
) -> tuple[UserProfile, date]:
    """Resolve an owned profile and a callback date."""
    profile = await get_user_profile(telegram_id, services)
    day_date = _parse_day(encoded_day)
    if profile is None or day_date is None:
        raise StaleCallback
    return profile, day_date


async def render_day(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    profile: UserProfile,
    day_date: date,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    form = await services.get_day().execute(GetDay(profile.id, day_date))
    events = tuple(
        await services.get_events_for_date().execute(
            GetEventsForDate(profile.id, day_date)
        )
    )
    await update_main_message(DayCardScreen(form=form, events=events))


def _today(profile: UserProfile) -> date:
    return datetime.now(UTC).astimezone(ZoneInfo(profile.timezone.name)).date()


def _parse_day(value: str) -> date | None:
    try:
        return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:]}")
    except ValueError:
        return None


async def _prompt_field(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    presentation_data: PresentationData,
    form: DayForm,
    field: Field,
    update_main_message: UpdateMainMessage,
    *,
    error: str | None = None,
) -> None:
    view = make_day_value_prompt_view(form, field)
    if view.kind is DayPromptKind.TEXT:
        await state.set_state(Diary.waiting_text)
        await presentation_data.write(DiaryTextData(form.day_date, field.id))
    await update_main_message(
        DayValuePromptScreen(view=view, error=error),
    )

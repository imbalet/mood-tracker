"""Handlers for filling, resuming and editing a daily entry."""

from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import (
    ConfirmReference,
    DayForm,
    GetDay,
    GetUserByTelegramId,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.errors import DayNotFound, FieldNotFound
from mood_tracker.domain.entities import Field, UserProfile
from mood_tracker.domain.errors import InvalidFieldValue
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    MenuCallback,
    MenuSection,
    OpenDayCallback,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.screens import (
    day_card_screen,
    day_value_prompt_screen,
    reference_review_screen,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.states import Diary
from mood_tracker.presentation.utils import UpdateMainMessage
from mood_tracker.presentation.view_models import (
    DayPromptKind,
    make_day_card_view,
    make_day_value_prompt_view,
    make_reference_review_view,
)

router = Router(name="today")


@router.message(Command("today"))
async def today(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the user-local day, continuing an existing draft when present."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await update_main_message(state, message, TEXTS[TextKey.START_FIRST])
        return
    await state.clear()
    await _render(
        message, state, profile, _today(profile), services, update_main_message
    )


@router.callback_query(MenuCallback.filter(F.section == MenuSection.TODAY))
async def open_today_from_menu(
    query: CallbackQueryWithMessage,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Start today's diary flow from the inline home screen."""
    profile = await _profile(telegram_id, services)
    if profile is None:
        await query.answer(TEXTS[TextKey.START_FIRST], show_alert=True)
        return
    await state.clear()
    await query.answer()
    await _render(query, state, profile, _today(profile), services, update_main_message)


@router.callback_query(DayValueCallback.filter())
async def save_value(
    query: CallbackQueryWithMessage,
    callback_data: DayValueCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist a Scale or Ordinal answer selected from an inline keyboard."""
    profile = await _profile(telegram_id, services)
    day_date = _parse_day(callback_data.day)
    if profile is None or day_date is None:
        await query.answer(TEXTS[TextKey.STALE_BUTTON], show_alert=True)
        return
    try:
        review = await services.save_day_value().execute(
            SaveDayValue(
                profile.id, day_date, callback_data.field_id, callback_data.value
            )
        )
    except FieldNotFound, InvalidFieldValue:
        await query.answer(TEXTS[TextKey.FIELD_VALUE_UNAVAILABLE], show_alert=True)
        return
    await state.clear()
    await query.answer()
    if review is not None:
        await update_main_message(
            state,
            query,
            reference_review_screen(make_reference_review_view(review)),
        )
    else:
        await _render(query, state, profile, day_date, services, update_main_message)


@router.callback_query(OpenDayCallback.filter())
async def open_day_card(
    query: CallbackQueryWithMessage,
    callback_data: OpenDayCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Return from an answer prompt to the selected day summary."""
    profile = await _profile(telegram_id, services)
    day_date = _parse_day(callback_data.day)
    if profile is None or day_date is None:
        await query.answer(TEXTS[TextKey.STALE_BUTTON], show_alert=True)
        return
    await state.clear()
    await query.answer()
    await _render(query, state, profile, day_date, services, update_main_message)


@router.callback_query(SkipTextCallback.filter())
async def skip_text(
    query: CallbackQueryWithMessage,
    callback_data: SkipTextCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist an explicit Text skip."""
    profile = await _profile(telegram_id, services)
    day_date = _parse_day(callback_data.day)
    if profile is None or day_date is None:
        await query.answer(TEXTS[TextKey.STALE_BUTTON], show_alert=True)
        return
    await services.skip_day_text().execute(
        SkipDayText(profile.id, day_date, callback_data.field_id)
    )
    await state.clear()
    await query.answer()
    await _render(query, state, profile, day_date, services, update_main_message)


@router.callback_query(ReferenceCallback.filter())
async def confirm_reference(
    query: CallbackQueryWithMessage,
    callback_data: ReferenceCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist the answer to a candidate best/worst reference day."""
    profile = await _profile(telegram_id, services)
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
    await _render(query, state, profile, _today(profile), services, update_main_message)


@router.callback_query(EditDayValueCallback.filter())
async def edit_value(
    query: CallbackQueryWithMessage,
    callback_data: EditDayValueCallback,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Prompt a field of an existing day for a replacement value."""
    profile = await _profile(telegram_id, services)
    day_date = _parse_day(callback_data.day)
    if profile is None or day_date is None:
        await query.answer(TEXTS[TextKey.STALE_BUTTON], show_alert=True)
        return
    form = await services.get_day().execute(GetDay(profile.id, day_date))
    field = next(
        (item for item in form.fields if item.id == callback_data.field_id), None
    )
    if field is None:
        await query.answer(TEXTS[TextKey.FIELD_UNAVAILABLE], show_alert=True)
        return
    await query.answer()
    await _prompt_field(query, state, form, field, update_main_message)


@router.message(Diary.waiting_text, F.text)
async def save_text(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    """Persist text supplied for the pending Text field."""
    profile = await _profile(telegram_id, services)
    data = await state.get_data()
    if (
        profile is None
        or not isinstance(data.get("day"), str)
        or not isinstance(data.get("field_id"), str)
    ):
        await state.clear()
        await update_main_message(state, message, TEXTS[TextKey.OPEN_TODAY_AGAIN])
        return
    day_date = _parse_day(data["day"])
    if day_date is None:
        await state.clear()
        await update_main_message(state, message, TEXTS[TextKey.OPEN_TODAY_AGAIN])
        return
    try:
        field_id = UUID(data["field_id"])
    except ValueError:
        await state.clear()
        await update_main_message(state, message, TEXTS[TextKey.OPEN_TODAY_AGAIN])
        return
    try:
        review = await services.save_day_value().execute(
            SaveDayValue(profile.id, day_date, field_id, message.text or "")
        )
    except FieldNotFound, InvalidFieldValue:
        form = await services.get_day().execute(GetDay(profile.id, day_date))
        field = next((item for item in form.fields if item.id == field_id), None)
        if field is None:
            await state.clear()
            await update_main_message(state, message, TEXTS[TextKey.OPEN_TODAY_AGAIN])
            return
        await _prompt_field(
            message,
            state,
            form,
            field,
            update_main_message,
            error=TEXTS[TextKey.TEXT_NOT_SAVED],
        )
        return
    await state.clear()
    if review is not None:
        await update_main_message(
            state,
            message,
            reference_review_screen(make_reference_review_view(review)),
        )
    else:
        await _render(message, state, profile, day_date, services, update_main_message)


async def _profile(
    telegram_id: int, services: ApplicationServices
) -> UserProfile | None:
    return await services.get_user_by_telegram_id().execute(
        GetUserByTelegramId(telegram_id)
    )


async def _render(
    event: Message | CallbackQueryWithMessage,
    state: FSMContext,
    profile: UserProfile,
    day_date: date,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    form = await services.get_day().execute(GetDay(profile.id, day_date))
    await update_main_message(state, event, day_card_screen(make_day_card_view(form)))


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
    form: DayForm,
    field: Field,
    update_main_message: UpdateMainMessage,
    *,
    error: str | None = None,
) -> None:
    view = make_day_value_prompt_view(form, field)
    if view.kind is DayPromptKind.TEXT:
        await state.set_state(Diary.waiting_text)
        await state.update_data(
            day=form.day_date.strftime("%Y%m%d"), field_id=str(field.id)
        )
    await update_main_message(
        state,
        event,
        day_value_prompt_screen(view, error=error),
    )

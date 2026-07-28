"""Handlers for filling, resuming and editing a daily entry."""

from datetime import UTC, date, datetime
from html import escape
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from mood_tracker.application.commands import (
    ConfirmReference,
    GetDay,
    GetUserByTelegramId,
    SaveDayValue,
    SkipDayText,
)
from mood_tracker.application.errors import DayNotFound, FieldNotFound
from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig, UserProfile
from mood_tracker.domain.errors import InvalidFieldValue
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    DayValueCallback,
    EditDayValueCallback,
    MenuCallback,
    MenuSection,
    ReferenceCallback,
    SkipTextCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.formatters import format_day_card
from mood_tracker.presentation.keyboards import (
    day_edit_keyboard,
    field_value_keyboard,
    reference_keyboard,
)
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.states import Diary
from mood_tracker.presentation.utils import UpdateMainMessage

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
        adjective = "лучше" if review.type.value == "best" else "хуже"
        await update_main_message(
            state,
            query,
            TEXTS[TextKey.REFERENCE_QUESTION].format(adjective=adjective),
            reply_markup=reference_keyboard(review),
        )
    else:
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
    await _prompt_field(query, state, day_date, field, update_main_message)


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
        review = await services.save_day_value().execute(
            SaveDayValue(
                profile.id, day_date, UUID(data["field_id"]), message.text or ""
            )
        )
    except ValueError, FieldNotFound, InvalidFieldValue:
        await update_main_message(
            state,
            message,
            TEXTS[TextKey.TEXT_NOT_SAVED],
        )
        return
    await state.clear()
    if review is not None:
        adjective = "лучше" if review.type.value == "best" else "хуже"
        await update_main_message(
            state,
            message,
            TEXTS[TextKey.REFERENCE_QUESTION].format(adjective=adjective),
            reply_markup=reference_keyboard(review),
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
    if form.next_field is None:
        await update_main_message(
            state, event, format_day_card(form), reply_markup=day_edit_keyboard(form)
        )
        return
    await _prompt_field(
        event, state, form.day_date, form.next_field, update_main_message
    )


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
    day_date: date,
    field: Field,
    update_main_message: UpdateMainMessage,
) -> None:
    if isinstance(field.current_version.config, (ScaleConfig, OrdinalConfig)):
        await update_main_message(
            state,
            event,
            TEXTS[TextKey.SELECT_VALUE].format(name=escape(field.name)),
            reply_markup=field_value_keyboard(field, day_date),
        )
        return
    await state.set_state(Diary.waiting_text)
    await state.update_data(day=day_date.strftime("%Y%m%d"), field_id=str(field.id))
    await update_main_message(
        state,
        event,
        TEXTS[TextKey.ENTER_TEXT].format(name=escape(field.name)),
        reply_markup=field_value_keyboard(field, day_date),
    )

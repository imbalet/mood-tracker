"""Telegram entry points for browsing diary dates and month images."""

from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, Message
from aiogram_calendar.schemas import SimpleCalAct, SimpleCalendarCallback

from mood_tracker.application.commands import GetMonthCalendar
from mood_tracker.presentation.callback_query import CallbackQueryWithMessage
from mood_tracker.presentation.callbacks import (
    CalendarImageAction,
    CalendarImageCallback,
    MenuCallback,
    MenuSection,
)
from mood_tracker.presentation.date_calendar import MoodDateCalendar
from mood_tracker.presentation.handlers.today import render_day
from mood_tracker.presentation.month_calendar import render_month_calendar
from mood_tracker.presentation.queries import get_user_profile
from mood_tracker.presentation.screens import main_menu_screen, month_calendar_screen
from mood_tracker.presentation.screens.screen import Screen
from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.state import PresentationData
from mood_tracker.presentation.utils import KeyboardBuilder, UpdateMainMessage

router = Router(name="calendar")


@router.callback_query(MenuCallback.filter(F.section == MenuSection.DATES))
@router.message(Command("dates"))
async def open_dates(
    event: Message | CallbackQueryWithMessage,
    *,
    telegram_id: int,
    state: FSMContext,
    services: ApplicationServices,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Open the current user-local month in the status-aware date picker."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await update_main_message(presentation_data, event, "Сначала используй /start.")
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    today = _today(profile.timezone.name)
    await _render_dates(
        event,
        presentation_data,
        profile.id,
        today.replace(day=1),
        today,
        services,
        update_main_message,
    )


@router.callback_query(SimpleCalendarCallback.filter())
async def browse_dates(
    query: CallbackQueryWithMessage,
    callback_data: SimpleCalendarCallback,
    *,
    telegram_id: int,
    state: FSMContext,
    services: ApplicationServices,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Handle aiogram-calendar navigation and open an owned selected day."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer("Сначала используй /start.", show_alert=True)
        return
    await state.set_state(None)
    await presentation_data.clear_flow()
    today = _today(profile.timezone.name)
    target = date(callback_data.year, callback_data.month, callback_data.day)
    if callback_data.act is SimpleCalAct.ignore:
        await query.answer()
        return
    if callback_data.act is SimpleCalAct.cancel:
        await update_main_message(presentation_data, query, main_menu_screen())
        return
    if callback_data.act is SimpleCalAct.day:
        if target > today:
            await query.answer("Будущую дату выбрать нельзя.", show_alert=True)
            return
        await render_day(
            query, presentation_data, profile, target, services, update_main_message
        )
        return
    month = _navigation_month(callback_data.act, target, today)
    await _render_dates(
        query,
        presentation_data,
        profile.id,
        month,
        today,
        services,
        update_main_message,
    )


@router.callback_query(MenuCallback.filter(F.section == MenuSection.CALENDAR))
@router.message(Command("calendar"))
async def open_month_image(
    event: Message | CallbackQueryWithMessage,
    *,
    telegram_id: int,
    state: FSMContext,
    services: ApplicationServices,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Render the user-local current month into the editable main screen."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        if not isinstance(event, Message):
            await event.answer("Сначала используй /start.", show_alert=True)
        else:
            await update_main_message(
                presentation_data, event, "Сначала используй /start."
            )
        return
    await state.set_state(None)
    month = _today(profile.timezone.name).replace(day=1)
    await _render_month(
        event,
        presentation_data,
        profile.id,
        month,
        False,
        services,
        update_main_message,
    )


@router.callback_query(CalendarImageCallback.filter())
async def browse_month_image(
    query: CallbackQueryWithMessage,
    callback_data: CalendarImageCallback,
    *,
    telegram_id: int,
    services: ApplicationServices,
    presentation_data: PresentationData,
    update_main_message: UpdateMainMessage,
) -> None:
    """Replace a calendar photo with the requested neighbouring owned month."""
    profile = await get_user_profile(telegram_id, services)
    if profile is None:
        await query.answer("Сначала используй /start.", show_alert=True)
        return
    current = date(callback_data.year, callback_data.month, 1)
    offset = -1 if callback_data.action is CalendarImageAction.PREVIOUS else 1
    month = _shift_month(current, offset)
    today_month = _today(profile.timezone.name).replace(day=1)
    if month > today_month:
        await query.answer("Будущего календаря ещё нет.", show_alert=True)
        return
    await _render_month(
        query,
        presentation_data,
        profile.id,
        month,
        month < today_month,
        services,
        update_main_message,
    )


async def _render_dates(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    user_id: UUID,
    month: date,
    today: date,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    data = await services.get_month_calendar().execute(GetMonthCalendar(user_id, month))
    statuses = {day.date: day.status for day in data.days}
    calendar = MoodDateCalendar(today, statuses)
    markup = await calendar.start_calendar(month.year, month.month)
    await update_main_message(
        presentation_data,
        event,
        Screen("<b>Выбери дату</b>\n✅ — завершён, 📝 — черновик.", markup),
    )


async def _month_image(
    user_id: UUID, month: date, services: ApplicationServices
) -> BufferedInputFile:
    data = await services.get_month_calendar().execute(GetMonthCalendar(user_id, month))
    return render_month_calendar(data)


async def _render_month(
    event: Message | CallbackQueryWithMessage,
    presentation_data: PresentationData,
    user_id: UUID,
    month: date,
    can_go_next: bool,
    services: ApplicationServices,
    update_main_message: UpdateMainMessage,
) -> None:
    image = await _month_image(user_id, month, services)
    await update_main_message(
        presentation_data,
        event,
        month_calendar_screen(image, _image_keyboard(month, can_go_next)),
    )


def _image_keyboard(month: date, can_go_next: bool) -> InlineKeyboardMarkup:
    builder = KeyboardBuilder()
    builder.row_buttons_text_tuple(
        (
            "←",
            CalendarImageCallback(
                action=CalendarImageAction.PREVIOUS, year=month.year, month=month.month
            ),
        ),
        *(
            (
                "→",
                CalendarImageCallback(
                    action=CalendarImageAction.NEXT,
                    year=month.year,
                    month=month.month,
                ),
            ),
        )
        if can_go_next
        else (),
    )
    builder.row_buttons_text_tuple(("В меню", MenuCallback(section=MenuSection.HOME)))
    return builder.as_markup()


def _navigation_month(action: SimpleCalAct, target: date, today: date) -> date:
    if action is SimpleCalAct.today:
        return today.replace(day=1)
    if action is SimpleCalAct.prev_y:
        shift = -12
    elif action is SimpleCalAct.next_y:
        shift = 12
    elif action is SimpleCalAct.prev_m:
        shift = -1
    else:
        shift = 1
    month = _shift_month(target.replace(day=1), shift)
    return min(month, today.replace(day=1))


def _shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def _today(timezone: str) -> date:
    return datetime.now(UTC).astimezone(ZoneInfo(timezone)).date()

"""Short-lived Telegram FSM states."""

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """Collect a timezone before creating a profile."""

    waiting_timezone = State()


class Diary(StatesGroup):
    """Wait for the message body of a Text field."""

    waiting_text = State()

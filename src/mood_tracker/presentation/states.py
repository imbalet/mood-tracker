"""Short-lived Telegram FSM states."""

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """Collect a timezone before creating a profile."""

    waiting_timezone = State()


class Diary(StatesGroup):
    """Wait for the message body of a Text field."""

    waiting_text = State()


class FieldForm(StatesGroup):
    """Collect short text input for field creation and settings."""

    waiting_name = State()
    waiting_scale = State()
    waiting_ordinal = State()
    waiting_ordinal_base = State()
    waiting_emoji = State()
    waiting_palette = State()

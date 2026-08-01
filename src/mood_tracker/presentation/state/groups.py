"""Aiogram states grouped by one user-facing form."""

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """Collect a timezone before creating a profile."""

    waiting_timezone = State()


class Diary(StatesGroup):
    """Collect the free-text value of a diary day."""

    waiting_text = State()


class EventFlow(StatesGroup):
    waiting_time = State()
    waiting_text = State()


class FieldCreation(StatesGroup):
    """Create a field from its name through semantic configuration."""

    waiting_name = State()
    waiting_scale = State()
    waiting_ordinal_base = State()
    waiting_ordinal_label = State()


class FieldRename(StatesGroup):
    """Collect a replacement field name."""

    waiting_name = State()


class FieldVersionChange(StatesGroup):
    """Collect a replacement Scale or Ordinal semantic configuration."""

    waiting_scale = State()
    waiting_ordinal_base = State()
    waiting_ordinal_label = State()


class FieldDisplayChange(StatesGroup):
    """Collect display-only field settings."""

    waiting_emoji = State()
    waiting_palette = State()

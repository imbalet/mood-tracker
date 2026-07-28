"""Public builders for complete Telegram screens."""

from mood_tracker.presentation.screens.diary import (
    day_card_screen,
    day_value_prompt_screen,
    reference_review_screen,
)
from mood_tracker.presentation.screens.fields import (
    field_card_screen,
    field_order_screen,
    fields_list_screen,
    palette_screen,
)
from mood_tracker.presentation.screens.menu import main_menu_screen
from mood_tracker.presentation.screens.screen import Screen, ScreenContent

__all__ = [
    "Screen",
    "ScreenContent",
    "day_card_screen",
    "day_value_prompt_screen",
    "field_card_screen",
    "field_order_screen",
    "fields_list_screen",
    "main_menu_screen",
    "palette_screen",
    "reference_review_screen",
]

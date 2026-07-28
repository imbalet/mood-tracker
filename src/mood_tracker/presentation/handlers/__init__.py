"""Public Telegram routers."""

from mood_tracker.presentation.handlers.fields import router as fields_router
from mood_tracker.presentation.handlers.menu import router as menu_router
from mood_tracker.presentation.handlers.onboarding import router as onboarding_router
from mood_tracker.presentation.handlers.today import router as today_router

__all__ = ["fields_router", "menu_router", "onboarding_router", "today_router"]

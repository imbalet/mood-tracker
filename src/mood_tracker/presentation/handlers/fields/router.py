"""Aggregate router for every field-management interaction."""

from aiogram import Router

from mood_tracker.presentation.handlers.fields.display import router as display_router
from mood_tracker.presentation.handlers.fields.form import router as form_router
from mood_tracker.presentation.handlers.fields.ordering import router as ordering_router
from mood_tracker.presentation.handlers.fields.overview import router as overview_router

router = Router(name="fields")
router.include_routers(overview_router, form_router, display_router, ordering_router)

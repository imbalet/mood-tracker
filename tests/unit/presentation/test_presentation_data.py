from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from mood_tracker.domain.enums import FieldType
from mood_tracker.presentation.state import (
    CreateFieldConfigData,
    CreateOrdinalData,
    DiaryTextData,
    InvalidPresentationData,
    PresentationData,
)


@pytest.mark.asyncio
async def test_presentation_data_round_trips_typed_payload() -> None:
    context = AsyncMock()
    context.get_data.return_value = {}
    storage = PresentationData(context)
    payload = CreateFieldConfigData(FieldType.SCALE, "Состояние")

    await storage.write(payload)

    context.get_data.return_value = context.update_data.call_args.kwargs
    assert await storage.require(CreateFieldConfigData) == payload


@pytest.mark.asyncio
async def test_clear_flow_preserves_main_screen_identifier() -> None:
    context = AsyncMock()
    context.get_data.return_value = {}
    storage = PresentationData(context)
    await storage.set_main_message_id(42)
    context.get_data.return_value = context.update_data.call_args.kwargs
    await storage.write(DiaryTextData(date(2025, 1, 2), UUID(int=1)))
    context.get_data.return_value = context.update_data.call_args.kwargs

    await storage.clear_flow()

    context.get_data.return_value = context.update_data.call_args.kwargs
    assert await storage.main_message_id() == 42
    with pytest.raises(InvalidPresentationData):
        await storage.require(DiaryTextData)


@pytest.mark.asyncio
async def test_require_rejects_mismatched_or_invalid_payload() -> None:
    context = AsyncMock()
    context.get_data.return_value = {
        "presentation": {
            "flow": {
                "kind": "diary_text",
                "payload": {"day_date": "not-a-date", "field_id": "bad"},
            }
        }
    }

    with pytest.raises(InvalidPresentationData):
        await PresentationData(context).require(DiaryTextData)


@pytest.mark.asyncio
async def test_ordinal_payload_uses_json_compatible_labels() -> None:
    context = AsyncMock()
    context.get_data.return_value = {}
    storage = PresentationData(context)
    payload = CreateOrdinalData("Плач", 0, ("Нет", "Немного"))

    await storage.write(payload)

    stored = context.update_data.call_args.kwargs["presentation"]
    assert stored["flow"]["payload"]["labels"] == ["Нет", "Немного"]

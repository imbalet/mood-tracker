"""Typed storage adapter over aiogram FSM data."""

from collections.abc import Mapping
from datetime import date
from typing import TypeVar, cast
from uuid import UUID

from aiogram.fsm.context import FSMContext

from mood_tracker.domain.enums import FieldType, QuestionnaireKind
from mood_tracker.presentation.state.data import (
    CreateFieldConfigData,
    CreateFieldNameData,
    CreateOrdinalData,
    DiaryTextData,
    EventInputData,
    FieldDisplayData,
    FieldVersionData,
    FlowData,
    RenameFieldData,
    VersionOrdinalData,
)

_ROOT_KEY = "presentation"
_SCREEN_KEY = "screen"
_FLOW_KEY = "flow"
FlowDataT = TypeVar("FlowDataT", bound=FlowData)


class InvalidPresentationData(ValueError):
    """Stored FSM data does not match the active presentation form."""


class PresentationData:
    """Read and write presentation payloads without exposing raw FSM mappings."""

    def __init__(self, context: FSMContext) -> None:
        self._context = context

    async def write(self, data: FlowData) -> None:
        """Replace the current form payload while preserving the screen reference."""
        root = await self._root()
        root[_FLOW_KEY] = {"kind": data.kind, "payload": data.to_payload()}
        await self._save(root)

    async def require(self, data_type: type[FlowDataT]) -> FlowDataT:
        """Return one expected payload or raise a recoverable validation error."""
        root = await self._root()
        flow = _mapping(root.get(_FLOW_KEY))
        if flow is None or flow.get("kind") != data_type.kind:
            raise InvalidPresentationData
        payload = _mapping(flow.get("payload"))
        if payload is None:
            raise InvalidPresentationData
        return cast(FlowDataT, _decode(data_type, payload))

    async def clear_flow(self) -> None:
        """Discard form data while retaining the current main screen identifier."""
        root = await self._root()
        root.pop(_FLOW_KEY, None)
        await self._save(root)

    async def main_message_id(self) -> int | None:
        """Return the current editable bot message identifier, if any."""
        screen = _mapping((await self._root()).get(_SCREEN_KEY))
        message_id = screen.get("message_id") if screen is not None else None
        return message_id if isinstance(message_id, int) else None

    async def set_main_message_id(self, message_id: int) -> None:
        """Persist the editable bot message identifier."""
        root = await self._root()
        root[_SCREEN_KEY] = {"message_id": message_id}
        await self._save(root)

    async def _root(self) -> dict[str, object]:
        raw = await self._context.get_data()
        root = _mapping(raw.get(_ROOT_KEY))
        return dict(root) if root is not None else {}

    async def _save(self, root: dict[str, object]) -> None:
        await self._context.update_data(**{_ROOT_KEY: root})


def _decode(data_type: type[FlowData], payload: Mapping[str, object]) -> FlowData:
    try:
        if data_type is CreateFieldNameData:
            return CreateFieldNameData(
                FieldType(_string(payload, "field_type")),
                QuestionnaireKind(_string(payload, "kind_value")),
            )
        if data_type is CreateFieldConfigData:
            return CreateFieldConfigData(
                FieldType(_string(payload, "field_type")),
                _string(payload, "name"),
                QuestionnaireKind(_string(payload, "kind_value")),
            )
        if data_type is RenameFieldData:
            return RenameFieldData(UUID(_string(payload, "field_id")))
        if data_type is FieldVersionData:
            return FieldVersionData(UUID(_string(payload, "field_id")))
        if data_type is CreateOrdinalData:
            return CreateOrdinalData(
                _string(payload, "name"),
                _ordinal_start(payload),
                _labels(payload),
                QuestionnaireKind(_string(payload, "kind_value")),
            )
        if data_type is VersionOrdinalData:
            return VersionOrdinalData(
                UUID(_string(payload, "field_id")),
                _ordinal_start(payload),
                _labels(payload),
            )
        if data_type is FieldDisplayData:
            return FieldDisplayData(UUID(_string(payload, "field_id")))
        if data_type is DiaryTextData:
            return DiaryTextData(
                date.fromisoformat(_string(payload, "day_date")),
                UUID(_string(payload, "field_id")),
            )
        if data_type is EventInputData:
            event_id = payload.get("event_id")
            field_id = payload.get("field_id")
            return EventInputData(
                UUID(event_id) if isinstance(event_id, str) else None,
                date.fromisoformat(_string(payload, "day_date")),
                UUID(field_id) if isinstance(field_id, str) else None,
            )
    except TypeError, ValueError:
        raise InvalidPresentationData from None
    raise InvalidPresentationData


def _mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise InvalidPresentationData
    return value


def _ordinal_start(payload: Mapping[str, object]) -> int:
    value = payload.get("starts_at")
    if value not in (0, 1):
        raise InvalidPresentationData
    return value


def _labels(payload: Mapping[str, object]) -> tuple[str, ...]:
    value = payload.get("labels")
    if not isinstance(value, list) or not all(
        isinstance(label, str) for label in value
    ):
        raise InvalidPresentationData
    return tuple(value)

"""UI-ready data for configurable diary-field screens."""

from dataclasses import dataclass
from uuid import UUID

from mood_tracker.domain.entities import Field, OrdinalConfig, ScaleConfig
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    FieldStatus,
    FieldType,
    QuestionnaireFieldRole,
)


@dataclass(frozen=True, slots=True)
class FieldListItemView:
    """One selectable field in the settings list."""

    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class FieldsListView:
    """A user-owned ordered field list."""

    items: tuple[FieldListItemView, ...]


@dataclass(frozen=True, slots=True)
class FieldCardView:
    """All data required by one field settings card."""

    id: UUID
    name: str
    status: FieldStatus
    type: FieldType
    is_core: bool
    semantic_text: str
    emoji: str | None
    show_in_calendar: bool
    version_count: int
    position: int
    palette_colors: tuple[str, str, str] | None


@dataclass(frozen=True, slots=True)
class FieldOrderItemView:
    """One field shown in the in-place order editor."""

    id: UUID
    name: str
    is_selected: bool


@dataclass(frozen=True, slots=True)
class FieldOrderView:
    """Fields plus the currently movable selected item."""

    items: tuple[FieldOrderItemView, ...]
    selected_id: UUID | None
    can_move_up: bool
    can_move_down: bool


@dataclass(frozen=True, slots=True)
class PaletteView:
    """Display data for the numbered core-state color legend."""

    field_id: UUID
    minimum: int
    maximum: int
    colors: tuple[str, str, str]


def make_fields_list_view(fields: tuple[Field, ...]) -> FieldsListView:
    """Map a field collection into a compact settings list."""
    return FieldsListView(
        tuple(FieldListItemView(field.id, field.name) for field in fields)
    )


def make_field_card_view(
    field: Field, placement: QuestionnaireField | None = None
) -> FieldCardView:
    """Map current field semantics and display settings into one card."""
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        semantic_text = f"Шкала: {config.minimum}–{config.maximum}"
    elif isinstance(config, OrdinalConfig):
        semantic_text = "Варианты: " + ", ".join(
            option.label for option in config.options
        )
    else:
        semantic_text = "Свободный текст"
    palette = field.display_config.state_palette
    is_core = (
        placement is not None and placement.role is QuestionnaireFieldRole.DAY_STATE
    ) or field.display_config.state_palette is not None
    return FieldCardView(
        id=field.id,
        name=field.name,
        status=(
            FieldStatus.ACTIVE
            if placement is None or placement.is_enabled
            else FieldStatus.INACTIVE
        ),
        type=field.current_version.type,
        is_core=is_core,
        semantic_text=semantic_text,
        emoji=field.display_config.emoji,
        show_in_calendar=field.display_config.show_in_calendar,
        version_count=len(field.versions),
        position=(placement.sort_order + 1) if placement is not None else 0,
        palette_colors=(palette.minimum, palette.middle, palette.maximum)
        if palette is not None
        else None,
    )


def make_field_order_view(
    fields: tuple[Field, ...], selected_id: UUID | None
) -> FieldOrderView:
    """Map field order and selection into move-button availability."""
    selected_index = next(
        (index for index, field in enumerate(fields) if field.id == selected_id), None
    )
    return FieldOrderView(
        items=tuple(
            FieldOrderItemView(field.id, field.name, field.id == selected_id)
            for field in fields
        ),
        selected_id=selected_id if selected_index is not None else None,
        can_move_up=selected_index is not None and selected_index > 0,
        can_move_down=selected_index is not None and selected_index < len(fields) - 1,
    )


def make_palette_view(
    field: Field, placement: QuestionnaireField | None = None
) -> PaletteView | None:
    """Return a core Scale palette ready for visual rendering, if configured."""
    config = field.current_version.config
    palette = field.display_config.state_palette
    if (
        (
            placement is not None
            and placement.role is not QuestionnaireFieldRole.DAY_STATE
        )
        or not isinstance(config, ScaleConfig)
        or palette is None
    ):
        return None
    return PaletteView(
        field_id=field.id,
        minimum=config.minimum,
        maximum=config.maximum,
        colors=(palette.minimum, palette.middle, palette.maximum),
    )

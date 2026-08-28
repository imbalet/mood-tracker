"""Complete Telegram screens for field settings and palette management."""

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import ClassVar, override
from uuid import UUID

from aiogram.types import (
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputRichMessage,
    InputRichMessageMedia,
)

from mood_tracker.application.contracts.questionnaires import (
    QuestionnaireFieldItem,
)
from mood_tracker.domain.entities import (
    Field,
    OrdinalConfig,
    ScaleConfig,
    StatePalette,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import (
    FieldType,
    MoveDirection,
    QuestionnaireFieldRole,
    QuestionnaireKind,
)
from mood_tracker.presentation.callbacks.callbacks import (
    AttachFieldCallback,
    FieldAction,
    FieldCallback,
    FieldCreateCallback,
    FieldMoveCallback,
    FieldsListAction,
    FieldsListCallback,
    MenuCallback,
    MenuSection,
    OrdinalBaseCallback,
    OrdinalDraftAction,
    OrdinalDraftCallback,
    PaletteCallback,
    PalettePreset,
    QuestionnaireFieldAction,
    QuestionnaireFieldCallback,
)
from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.rendering.palette_preview import render_palette_preview
from mood_tracker.presentation.screens.screen import Screen, ScreenContent
from mood_tracker.presentation.state.data import CreateOrdinalData, VersionOrdinalData


@dataclass
class FieldListScreen(Screen):
    items: tuple[QuestionnaireFieldItem, ...]
    kind: QuestionnaireKind

    @override
    def _text(self) -> ScreenContent:
        return (
            "\n\n".join((TEXTS[TextKey.FIELDS_TITLE], TEXTS[TextKey.NO_FIELDS]))
            if not self.items
            else TEXTS[TextKey.FIELDS_TITLE]
        )

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        for item in self.items:
            self._kbuilder.row(
                (
                    item.field.name,
                    FieldCallback(
                        action=FieldAction.OPEN, field_id=item.field.id, kind=self.kind
                    ),
                )
            )
        self._kbuilder.row(
            (
                TextKey.ADD_FIELD,
                FieldsListCallback(action=FieldsListAction.CREATE, kind=self.kind),
            )
        ).row(
            (
                TextKey.ADD_FROM_QUESTIONNAIRE,
                FieldsListCallback(action=FieldsListAction.ATTACH, kind=self.kind),
            )
        ).row(
            (
                TextKey.FIELD_REORDER,
                FieldsListCallback(action=FieldsListAction.ORDER, kind=self.kind),
            )
        ).row((TextKey.BACK_TO_MENU, MenuCallback(section=MenuSection.HOME)))
        return self._kbuilder.as_markup()


@dataclass(frozen=True, slots=True)
class FieldCardView:
    """All data required by one field settings card."""

    id: UUID
    name: str
    is_enabled: bool
    type: FieldType
    is_core: bool
    is_system: bool
    semantic_text: str
    emoji: str | None
    show_in_calendar: bool
    version_count: int
    position: int
    palette_colors: tuple[str, str, str] | None
    is_required: bool = False
    can_detach: bool = False
    kind: QuestionnaireKind = QuestionnaireKind.DAY


def make_field_card_view(
    field: Field,
    placement: QuestionnaireField | None = None,
    kind: QuestionnaireKind = QuestionnaireKind.DAY,
) -> FieldCardView:
    """Map current field semantics and display settings into one card."""
    config = field.current_version.config
    if isinstance(config, ScaleConfig):
        semantic_text = f"{TEXTS[TextKey.FIELD_TYPE_SCALE_SHORT]}: {config.minimum}–{config.maximum}"  # noqa: E501
    elif isinstance(config, OrdinalConfig):
        semantic_text = f"{TEXTS[TextKey.FIELD_TYPE_ORDINAL_SHORT]}: " + ", ".join(
            option.label for option in config.options
        )
    else:
        semantic_text = TEXTS[TextKey.FIELD_TYPE_TEXT]
    palette = field.display_config.state_palette
    is_core = (
        placement is not None and placement.role is QuestionnaireFieldRole.DAY_STATE
    ) or field.display_config.state_palette is not None
    is_system = (
        placement is not None and placement.role is not QuestionnaireFieldRole.ORDINARY
    )
    return FieldCardView(
        id=field.id,
        name=field.name,
        is_enabled=placement is None or placement.is_enabled,
        type=field.current_version.type,
        is_core=is_core,
        is_system=is_system,
        semantic_text=semantic_text,
        emoji=field.display_config.emoji,
        show_in_calendar=field.display_config.show_in_calendar,
        version_count=len(field.versions),
        position=(placement.sort_order + 1) if placement is not None else 0,
        palette_colors=(palette.minimum, palette.middle, palette.maximum)
        if palette is not None
        else None,
        is_required=placement.is_required if placement is not None else False,
        can_detach=(
            placement is not None and placement.role is QuestionnaireFieldRole.ORDINARY
        ),
        kind=kind,
    )


@dataclass
class FieldCardScreen(Screen):
    view: FieldCardView

    @override
    def _text(self) -> ScreenContent:
        enabled_text = TEXTS[
            TextKey.FIELD_ENABLED if self.view.is_enabled else TextKey.FIELD_DISABLED
        ]
        lines = [
            TEXTS[TextKey.FIELD_DETAILS].format(name=escape(self.view.name)),
            f"Тип: {_field_type_label(self.view.type)}",
            f"Статус: <b>{enabled_text}</b>",
            (
                f"В анкете: {'обязательное' if self.view.is_required else 'необязательное'}"  # noqa: E501
                if self.view.kind.value == "event"
                else ""
            ),
            escape(self.view.semantic_text),
            f"Emoji: {escape(self.view.emoji or '—')}",
            f"Показывать в календаре: {'да' if self.view.show_in_calendar else 'нет'}",
            f"Версий значений: {self.view.version_count}",
            TEXTS[TextKey.FIELD_POSITION].format(position=self.view.position),
        ]
        if self.view.palette_colors is not None:
            minimum, middle, maximum = self.view.palette_colors
            lines.append(f"Палитра: <code>{minimum} → {middle} → {maximum}</code>")
        return "\n".join(line for line in lines if line)

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        # TODO: придумать как уменьшить дублирование
        self._kbuilder.row(
            (
                TextKey.FIELD_RENAME,
                FieldCallback(
                    action=FieldAction.RENAME,
                    field_id=self.view.id,
                    kind=self.view.kind,
                ),
            )
        )

        version_key = {
            FieldType.SCALE: TextKey.FIELD_CHANGE_RANGE,
            FieldType.ORDINAL: TextKey.FIELD_CHANGE_OPTIONS,
        }.get(self.view.type)

        if version_key is not None:
            self._kbuilder.row(
                (
                    version_key,
                    FieldCallback(
                        action=FieldAction.VERSION,
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        self._kbuilder.row(
            (
                TextKey.FIELD_EMOJI,
                FieldCallback(
                    action=FieldAction.EMOJI, field_id=self.view.id, kind=self.view.kind
                ),
            ),
            (
                TextKey.FIELD_CLEAR_EMOJI,
                FieldCallback(
                    action=FieldAction.CLEAR_EMOJI,
                    field_id=self.view.id,
                    kind=self.view.kind,
                ),
            ),
        )
        if self.view.kind.value == "day":
            self._kbuilder.row(
                (
                    TextKey.FIELD_TOGGLE_CALENDAR,
                    FieldCallback(
                        action=FieldAction.TOGGLE_CALENDAR,
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        if self.view.is_core:
            self._kbuilder.row(
                (
                    TextKey.FIELD_PALETTE,
                    FieldCallback(
                        action=FieldAction.PALETTE,
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        elif not self.view.is_system:
            self._kbuilder.row(
                (
                    TEXTS[
                        TextKey.FIELD_DISABLE
                        if self.view.is_enabled
                        else TextKey.FIELD_ENABLE
                    ],
                    QuestionnaireFieldCallback(
                        action=(
                            QuestionnaireFieldAction.DISABLE
                            if self.view.is_enabled
                            else QuestionnaireFieldAction.ENABLE
                        ),
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        if self.view.kind.value == "event":
            self._kbuilder.row(
                (
                    "Сделать необязательным"
                    if self.view.is_required
                    else "Сделать обязательным",
                    QuestionnaireFieldCallback(
                        action=QuestionnaireFieldAction.TOGGLE_REQUIRED,
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        if self.view.can_detach:
            self._kbuilder.row(
                (
                    TextKey.FIELD_DELETE,
                    FieldCallback(
                        action=FieldAction.DELETE,
                        field_id=self.view.id,
                        kind=self.view.kind,
                    ),
                )
            )
        self._kbuilder.row((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
        return self._kbuilder.as_markup()


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
    kind: QuestionnaireKind = QuestionnaireKind.DAY


def make_field_order_view(
    fields: tuple[Field, ...],
    selected_id: UUID | None,
    kind: QuestionnaireKind = QuestionnaireKind.DAY,
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
        kind=kind,
    )


@dataclass
class FieldOrderScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.FIELD_ORDER_TITLE]

    view: FieldOrderView

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        for item in self.view.items:
            label = (
                TEXTS[TextKey.FIELD_ORDER_SELECTED].format(name=item.name)
                if item.is_selected
                else item.name
            )
            self._kbuilder.row(
                (
                    label,
                    FieldCallback(
                        action=FieldAction.ORDER, field_id=item.id, kind=self.view.kind
                    ),
                )
            )
        if self.view.selected_id is not None:
            move_buttons = []
            if self.view.can_move_up:
                move_buttons.append(
                    (
                        TEXTS[TextKey.FIELD_MOVE_UP],
                        FieldMoveCallback(
                            field_id=self.view.selected_id,
                            direction=MoveDirection.UP,
                            kind=self.view.kind,
                        ),
                    )
                )
            if self.view.can_move_down:
                move_buttons.append(
                    (
                        TEXTS[TextKey.FIELD_MOVE_DOWN],
                        FieldMoveCallback(
                            field_id=self.view.selected_id,
                            direction=MoveDirection.DOWN,
                            kind=self.view.kind,
                        ),
                    )
                )
            if move_buttons:
                self._kbuilder.row(*move_buttons)
            self._kbuilder.row(
                (TextKey.FIELD_ORDER_DONE, MenuCallback(section=MenuSection.FIELDS))
            )
        self._kbuilder.row((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
        return self._kbuilder.as_markup()


@dataclass(frozen=True, slots=True)
class PaletteView:
    """Display data for the numbered core-state color legend."""

    field_id: UUID
    minimum: int
    maximum: int
    colors: tuple[str, str, str]


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


@dataclass
class PaletteScreen(Screen):
    view: PaletteView

    @override
    def _text(self) -> ScreenContent:
        minimum, middle, maximum = self.view.colors
        config = ScaleConfig(self.view.minimum, self.view.maximum)
        palette = StatePalette(minimum, middle, maximum)
        return InputRichMessage(
            html=(
                "<h3>Палитра состояния</h3>"
                '<img src="tg://photo?id=scale"/>'
                "<p><code>"
                f"{minimum} → {middle} → {maximum}"
                "</code></p>"
            ),
            media=[
                InputRichMessageMedia(
                    id="scale",
                    media=InputMediaPhoto(
                        media=render_palette_preview(config, palette)
                    ),
                )
            ],
        )

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        for preset, text_key in (
            (PalettePreset.WARM, TextKey.PALETTE_WARM),
            (PalettePreset.FOREST, TextKey.PALETTE_FOREST),
            (PalettePreset.COOL, TextKey.PALETTE_COOL),
            (PalettePreset.CUSTOM, TextKey.PALETTE_CUSTOM),
        ):
            self._kbuilder.row(
                (
                    TEXTS[text_key],
                    PaletteCallback(field_id=self.view.field_id, preset=preset),
                )
            )
        self._kbuilder.row(
            (
                TextKey.BACK,
                FieldCallback(action=FieldAction.OPEN, field_id=self.view.field_id),
            )
        )
        return self._kbuilder.as_markup()


@dataclass
class InvalidateScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.INVALID_FIELD_INPUT]


@dataclass
class InputErrorScreen(Screen):
    error: str
    prompt: str

    @override
    def _text(self) -> ScreenContent:
        return f"{self.error}\n\n{self.prompt}"


def _field_type_label(type: FieldType) -> str:
    return TEXTS[
        {
            FieldType.SCALE: TextKey.FIELD_TYPE_SCALE,
            FieldType.ORDINAL: TextKey.FIELD_TYPE_ORDINAL,
            FieldType.TEXT: TextKey.FIELD_TYPE_TEXT,
        }[type]
    ]


@dataclass
class PromptEmojiScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.EMOJI_PROMPT]


@dataclass
class DeleteConfirmationScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.FIELD_DELETE_PROMPT]

    field_id: UUID
    kind: QuestionnaireKind

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            (
                TextKey.FIELD_DELETE_CONFIRM,
                FieldCallback(
                    action=FieldAction.CONFIRM_DELETE,
                    field_id=self.field_id,
                    kind=self.kind,
                ),
            )
        ).row(
            (
                TextKey.BACK,
                FieldCallback(
                    action=FieldAction.OPEN,
                    field_id=self.field_id,
                    kind=self.kind,
                ),
            )
        )
        return self._kbuilder.as_markup()


@dataclass
class FieldNamePromptScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.FIELD_NAME_PROMPT]


@dataclass
class ScaleBoundariesScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.SCALE_PROMPT]


@dataclass
class OrdinalFirstOptionDisplayScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.ORDINAL_BASE_PROMPT]

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            (TextKey.ORDINAL_HIDDEN_ZERO, OrdinalBaseCallback(value=0))
        ).row((TextKey.ORDINAL_VISIBLE_ONE, OrdinalBaseCallback(value=1)))
        return self._kbuilder.as_markup()


@dataclass
class OrdinalDraftScreen(Screen):
    draft: CreateOrdinalData | VersionOrdinalData

    @override
    def _text(self) -> ScreenContent:
        options = (
            "\n".join(
                f"{index}. {escape(label)}"
                for index, label in enumerate(self.draft.labels, start=1)
            )
            or "—"
        )
        prompt = (
            TEXTS[TextKey.ORDINAL_NEXT_PROMPT]
            if self.draft.labels
            else TEXTS[TextKey.ORDINAL_FIRST_PROMPT]
        )
        text = "\n\n".join(
            part
            for part in (
                TEXTS[TextKey.ORDINAL_DRAFT].format(options=options),
                prompt,
            )
            if part
        )
        return text

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        label_count = len(self.draft.labels)
        if label_count:
            self._kbuilder.row(
                (
                    TextKey.ORDINAL_REMOVE,
                    OrdinalDraftCallback(action=OrdinalDraftAction.REMOVE),
                ),
                (
                    TextKey.ORDINAL_RESET,
                    OrdinalDraftCallback(action=OrdinalDraftAction.RESET),
                ),
            )
        if label_count >= 2:
            self._kbuilder.row(
                (
                    TextKey.ORDINAL_FINISH,
                    OrdinalDraftCallback(action=OrdinalDraftAction.FINISH),
                )
            )
        return self._kbuilder.as_markup()


@dataclass
class FieldSettingsQuestionnaireSelectScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.QUESTIONNAIRES_TITLE]

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            (
                TextKey.DIARY,
                FieldsListCallback(
                    action=FieldsListAction.SELECT, kind=QuestionnaireKind.DAY
                ),
            ),
            (
                TextKey.EVENTS,
                FieldsListCallback(
                    action=FieldsListAction.SELECT, kind=QuestionnaireKind.EVENT
                ),
            ),
        )
        return self._kbuilder.as_markup()


@dataclass
class ChooseFieldTypeScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.CREATE_FIELD_TYPE]

    kind: QuestionnaireKind

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        self._kbuilder.row(
            (
                TextKey.FIELD_TYPE_SCALE,
                FieldCreateCallback(type=FieldType.SCALE, kind=self.kind),
            )
        ).row(
            (
                TextKey.FIELD_TYPE_ORDINAL,
                FieldCreateCallback(type=FieldType.ORDINAL, kind=self.kind),
            )
        ).row(
            (
                TextKey.FIELD_TYPE_TEXT,
                FieldCreateCallback(type=FieldType.TEXT, kind=self.kind),
            )
        ).row((TextKey.BACK, MenuCallback(section=MenuSection.FIELDS)))
        return self._kbuilder.as_markup()


@dataclass
class AddFieldFromAnotherScreen(Screen):
    text: ClassVar[str | None] = TEXTS[TextKey.ADD_FROM_QUESTIONNAIRE]

    candidates: Sequence[QuestionnaireFieldItem]
    current: set[UUID]
    kind: QuestionnaireKind

    @override
    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        for item in self.candidates:
            if item.field.id not in self.current:
                self._kbuilder.row(
                    (
                        item.field.name,
                        AttachFieldCallback(field_id=item.field.id, kind=self.kind),
                    )
                )
        self._kbuilder.row(
            (
                TextKey.BACK,
                FieldsListCallback(action=FieldsListAction.SELECT, kind=self.kind),
            )
        )
        return self._kbuilder.as_markup()

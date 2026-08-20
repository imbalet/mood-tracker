"""A complete Telegram screen ready for delivery."""

from dataclasses import dataclass, field
from html import escape
from typing import ClassVar

from aiogram.types import InlineKeyboardMarkup, InputRichMessage

from mood_tracker.presentation.constants import TEXTS, TextKey
from mood_tracker.presentation.utils.keyboard_builder import KeyboardBuilder

ScreenContent = str | InputRichMessage


@dataclass(frozen=True, slots=True)
class ScreenResult:
    """Pair one screen's content with its inline controls."""

    content: ScreenContent
    reply_markup: InlineKeyboardMarkup | None = None


@dataclass(kw_only=True)
class Screen:
    KEYBOARD_ROW_WIDTH: ClassVar[int] = 2

    # TODO: сделать еще и TextKey
    text: ClassVar[str | None] = None

    notice: str | TextKey | None = None

    _kbuilder: KeyboardBuilder = field(init=False)

    def __post_init__(self) -> None:
        self._kbuilder = KeyboardBuilder(row_width=self.KEYBOARD_ROW_WIDTH)

    def _text(self) -> ScreenContent:
        if self.text is None:
            raise NotImplementedError("Screen text is not defined")
        return self.text

    def _reply_markup(self) -> InlineKeyboardMarkup | None:
        return None

    def _render_text(self) -> ScreenContent:
        content = self._text()

        if self.notice is None:
            return content

        notice = TEXTS[self.notice] if isinstance(self.notice, TextKey) else self.notice

        if isinstance(content, str):
            return f"{notice}\n\n{content}"

        return InputRichMessage(
            html=f"<p>{escape(notice)}</p>{content.html}",
            media=content.media,
            is_rtl=content.is_rtl,
            skip_entity_detection=content.skip_entity_detection,
        )

    def render(self) -> ScreenResult:
        return ScreenResult(
            content=self._render_text(),
            reply_markup=self._reply_markup(),
        )

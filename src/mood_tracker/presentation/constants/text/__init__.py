"""Russian interface copy keyed independently from Telegram handlers."""

from collections import defaultdict
from warnings import warn

from . import fields, fields_settings, menu, settings, system
from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    **menu._TEXTS,
    **system._TEXTS,
    **fields_settings._TEXTS,
    **settings._TEXTS,
    **fields._TEXTS,
    # event
    TextKey.EVENT_SAVED: (
        "⏳ Событие сохранено как черновик. Позже его можно будет дополнить."
    ),
    TextKey.EVENT_NOT_SAVED: "Не удалось сохранить событие. Попробуй ещё раз.",
}


def _missing_text() -> str:
    warn("No translation for key", stacklevel=2)
    return "<?>"


TEXTS = defaultdict(_missing_text, _TEXTS)


__all__ = ["TEXTS", "TextKey"]

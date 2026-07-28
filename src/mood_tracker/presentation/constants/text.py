"""Russian interface copy keyed independently from Telegram handlers."""

from collections import defaultdict
from enum import StrEnum
from warnings import warn


class TextKey(StrEnum):
    """Stable keys for static presentation text."""

    MENU_TITLE = "menu_title"
    MENU_TODAY = "menu_today"
    MENU_FIELDS = "menu_fields"
    MENU_RECORDS = "menu_records"
    MENU_SETTINGS = "menu_settings"
    BACK_TO_MENU = "back_to_menu"
    BACK = "back"
    SKIP = "skip"
    YES = "yes"
    NO = "no"
    START_DIARY = "start_diary"
    ALREADY_REGISTERED = "already_registered"
    START_FIRST = "start_first"
    ONBOARDING_GREETING = "onboarding_greeting"
    ENTER_TIMEZONE = "enter_timezone"
    INVALID_TIMEZONE = "invalid_timezone"
    TIMEZONE_SAVED = "timezone_saved"
    STALE_BUTTON = "stale_button"
    FIELD_VALUE_UNAVAILABLE = "field_value_unavailable"
    FIELD_UNAVAILABLE = "field_unavailable"
    DAY_UNAVAILABLE = "day_unavailable"
    TEXT_NOT_SAVED = "text_not_saved"
    OPEN_TODAY_AGAIN = "open_today_again"
    SELECT_VALUE = "select_value"
    ENTER_TEXT = "enter_text"
    REFERENCE_QUESTION = "reference_question"
    EMPTY_DAY = "empty_day"
    EDIT_FIELD = "edit_field"


_TEXTS: dict[TextKey, str] = {
    TextKey.MENU_TITLE: "<b>Дневник состояния</b>\nВыбери, что хочешь сделать.",
    TextKey.MENU_TODAY: "📝 Сегодня",
    TextKey.MENU_FIELDS: "⚙️ Поля",
    TextKey.MENU_RECORDS: "🏔️ Личные ориентиры",
    TextKey.MENU_SETTINGS: "Настройки",
    TextKey.BACK_TO_MENU: "🏠 В меню",
    TextKey.BACK: "← Назад",
    TextKey.SKIP: "Пропустить",
    TextKey.YES: "Да",
    TextKey.NO: "Нет",
    TextKey.START_DIARY: "Открыть дневник",
    TextKey.ALREADY_REGISTERED: "Ты уже зарегистрирован.",
    TextKey.START_FIRST: "Сначала создай дневник командой /start.",
    TextKey.ONBOARDING_GREETING: (
        "Привет! Выбери свой часовой пояс — по нему бот определяет дату записи "
        "и время напоминаний."
    ),
    TextKey.ENTER_TIMEZONE: "Отправь IANA-имя, например <code>Asia/Tokyo</code>.",
    TextKey.INVALID_TIMEZONE: (
        "Не удалось распознать часовой пояс. Например: <code>Europe/Moscow</code>."
    ),
    TextKey.TIMEZONE_SAVED: "Готово! Часовой пояс: <b>{timezone}</b>.",
    TextKey.STALE_BUTTON: "Кнопка устарела.",
    TextKey.FIELD_VALUE_UNAVAILABLE: (
        "Это значение больше недоступно. Открой /today заново."
    ),
    TextKey.FIELD_UNAVAILABLE: "Поле больше недоступно.",
    TextKey.DAY_UNAVAILABLE: "Запись больше недоступна.",
    TextKey.TEXT_NOT_SAVED: (
        "Текст не сохранён. Отправь непустой текст или нажми «Пропустить»."
    ),
    TextKey.OPEN_TODAY_AGAIN: "Открой /today и попробуй ещё раз.",
    TextKey.SELECT_VALUE: "<b>{name}</b>\nВыбери значение.",
    TextKey.ENTER_TEXT: "<b>{name}</b>\nОтправь текст или пропусти этот шаг.",
    TextKey.REFERENCE_QUESTION: "Сегодня {adjective} твоего текущего рекордного дня?",
    TextKey.EMPTY_DAY: "За этот день пока нет записи.",
    TextKey.EDIT_FIELD: "Изменить: {name}",
}


def _missing_text() -> str:
    warn("No translation for key", stacklevel=2)
    return "<?>"


TEXTS = defaultdict(_missing_text, _TEXTS)

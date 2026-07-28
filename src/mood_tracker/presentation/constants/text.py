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
    FIELDS_TITLE = "fields_title"
    NO_FIELDS = "no_fields"
    ADD_FIELD = "add_field"
    CREATE_FIELD_TYPE = "create_field_type"
    FIELD_TYPE_SCALE = "field_type_scale"
    FIELD_TYPE_ORDINAL = "field_type_ordinal"
    FIELD_TYPE_TEXT = "field_type_text"
    FIELD_NAME_PROMPT = "field_name_prompt"
    SCALE_PROMPT = "scale_prompt"
    ORDINAL_PROMPT = "ordinal_prompt"
    ORDINAL_BASE_PROMPT = "ordinal_base_prompt"
    ORDINAL_HIDDEN_ZERO = "ordinal_hidden_zero"
    ORDINAL_VISIBLE_ONE = "ordinal_visible_one"
    ORDINAL_FIRST_PROMPT = "ordinal_first_prompt"
    ORDINAL_NEXT_PROMPT = "ordinal_next_prompt"
    ORDINAL_DRAFT = "ordinal_draft"
    ORDINAL_ADD = "ordinal_add"
    ORDINAL_REMOVE = "ordinal_remove"
    ORDINAL_RESET = "ordinal_reset"
    ORDINAL_FINISH = "ordinal_finish"
    FIELD_CREATED = "field_created"
    FIELD_RENAMED = "field_renamed"
    FIELD_CONFIG_SAVED = "field_config_saved"
    FIELD_STATUS_ACTIVE = "field_status_active"
    FIELD_STATUS_INACTIVE = "field_status_inactive"
    FIELD_STATUS_HIDDEN = "field_status_hidden"
    FIELD_RENAME = "field_rename"
    FIELD_NEW_VERSION = "field_new_version"
    FIELD_CHANGE_RANGE = "field_change_range"
    FIELD_CHANGE_OPTIONS = "field_change_options"
    FIELD_REORDER = "field_reorder"
    FIELD_EMOJI = "field_emoji"
    FIELD_CLEAR_EMOJI = "field_clear_emoji"
    FIELD_TOGGLE_CALENDAR = "field_toggle_calendar"
    FIELD_PALETTE = "field_palette"
    FIELD_MOVE_UP = "field_move_up"
    FIELD_MOVE_DOWN = "field_move_down"
    FIELD_DETAILS = "field_details"
    EMOJI_PROMPT = "emoji_prompt"
    PALETTE_PROMPT = "palette_prompt"
    PALETTE_TITLE = "palette_title"
    PALETTE_WARM = "palette_warm"
    PALETTE_FOREST = "palette_forest"
    PALETTE_COOL = "palette_cool"
    PALETTE_CUSTOM = "palette_custom"
    FIELD_POSITION = "field_position"
    FIELD_ORDER_TITLE = "field_order_title"
    FIELD_ORDER_SELECTED = "field_order_selected"
    FIELD_ORDER_DONE = "field_order_done"
    INVALID_FIELD_INPUT = "invalid_field_input"
    INVALID_SCALE_INPUT = "invalid_scale_input"
    INVALID_PALETTE_INPUT = "invalid_palette_input"


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
    TextKey.FIELDS_TITLE: "<b>Поля дневника</b>\nВыбери поле для настройки.",
    TextKey.NO_FIELDS: "Пока нет пользовательских полей.",
    TextKey.ADD_FIELD: "＋ Добавить поле",
    TextKey.CREATE_FIELD_TYPE: "Какой тип поля добавить?",
    TextKey.FIELD_TYPE_SCALE: "Числовая шкала",
    TextKey.FIELD_TYPE_ORDINAL: "Упорядоченные варианты",
    TextKey.FIELD_TYPE_TEXT: "Свободный текст",
    TextKey.FIELD_NAME_PROMPT: "Напиши название поля.",
    TextKey.SCALE_PROMPT: (
        "Укажи границы шкалы через пробел, например <code>0 10</code>."
    ),
    TextKey.ORDINAL_PROMPT: "Добавь варианты в нужном порядке.",
    TextKey.ORDINAL_BASE_PROMPT: "Как отображать первый вариант в календаре?",
    TextKey.ORDINAL_HIDDEN_ZERO: "Не показывать «нет»",
    TextKey.ORDINAL_VISIBLE_ONE: "Показывать все варианты",
    TextKey.ORDINAL_FIRST_PROMPT: "Напиши первый вариант.",
    TextKey.ORDINAL_NEXT_PROMPT: "Напиши следующий вариант.",
    TextKey.ORDINAL_DRAFT: "<b>Варианты</b>\n{options}",
    TextKey.ORDINAL_ADD: "Добавить вариант",
    TextKey.ORDINAL_REMOVE: "Удалить последний",
    TextKey.ORDINAL_RESET: "Начать заново",
    TextKey.ORDINAL_FINISH: "Готово",
    TextKey.FIELD_CREATED: "Поле создано.",
    TextKey.FIELD_RENAMED: "Название поля изменено.",
    TextKey.FIELD_CONFIG_SAVED: "Настройки сохранены.",
    TextKey.FIELD_STATUS_ACTIVE: "Активно",
    TextKey.FIELD_STATUS_INACTIVE: "Неактивно",
    TextKey.FIELD_STATUS_HIDDEN: "Скрыто",
    TextKey.FIELD_RENAME: "Переименовать",
    TextKey.FIELD_NEW_VERSION: "Изменить значения",
    TextKey.FIELD_CHANGE_RANGE: "Изменить диапазон",
    TextKey.FIELD_CHANGE_OPTIONS: "Изменить варианты",
    TextKey.FIELD_REORDER: "Изменить порядок",
    TextKey.FIELD_EMOJI: "Изменить emoji",
    TextKey.FIELD_CLEAR_EMOJI: "Убрать emoji",
    TextKey.FIELD_TOGGLE_CALENDAR: "Показывать в календаре",
    TextKey.FIELD_PALETTE: "Палитра состояния",
    TextKey.FIELD_MOVE_UP: "↑ Выше",
    TextKey.FIELD_MOVE_DOWN: "↓ Ниже",
    TextKey.FIELD_DETAILS: "Поле: <b>{name}</b>",
    TextKey.EMOJI_PROMPT: "Отправь emoji для этого поля.",
    TextKey.PALETTE_PROMPT: (
        "Отправь три цвета через пробел: минимум, нейтральное значение и максимум. "
        "Например <code>#D9534F #F0E68C #5CB85C</code>."
    ),
    TextKey.PALETTE_TITLE: "<b>Палитра состояния</b>\nВыбери вариант или задай свой.",
    TextKey.PALETTE_WARM: "Тёплая палитра",
    TextKey.PALETTE_FOREST: "Лесная палитра",
    TextKey.PALETTE_COOL: "Холодная палитра",
    TextKey.PALETTE_CUSTOM: "Свои HEX-цвета",
    TextKey.FIELD_POSITION: "Позиция: <b>{position}</b>",
    TextKey.FIELD_ORDER_TITLE: "<b>Порядок полей</b>\nВыбери поле для перемещения.",
    TextKey.FIELD_ORDER_SELECTED: "✅ {name}",
    TextKey.FIELD_ORDER_DONE: "Готово",
    TextKey.INVALID_FIELD_INPUT: (
        "Не удалось сохранить. Проверь формат и попробуй ещё раз."
    ),
    TextKey.INVALID_SCALE_INPUT: (
        "⚠️ Нужны два целых числа: минимум и максимум. Например <code>0 10</code>."
    ),
    TextKey.INVALID_PALETTE_INPUT: (
        "⚠️ Нужны три HEX-цвета через пробел. Например "
        "<code>#D9534F #F0E68C #5CB85C</code>."
    ),
}


def _missing_text() -> str:
    warn("No translation for key", stacklevel=2)
    return "<?>"


TEXTS = defaultdict(_missing_text, _TEXTS)

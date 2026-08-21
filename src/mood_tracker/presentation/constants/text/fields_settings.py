from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
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
    TextKey.ORDINAL_REMOVE: "Удалить последний",
    TextKey.ORDINAL_RESET: "Начать заново",
    TextKey.ORDINAL_FINISH: "Готово",
    TextKey.FIELD_CREATED: "Поле создано.",
    TextKey.FIELD_RENAMED: "Название поля изменено.",
    TextKey.FIELD_CONFIG_SAVED: "Настройки сохранены.",
    TextKey.FIELD_ENABLED: "Активно",
    TextKey.FIELD_DISABLED: "Отключено",
    TextKey.FIELD_ENABLE: "Включить в анкете",
    TextKey.FIELD_DISABLE: "Отключить в анкете",
    TextKey.FIELD_DELETE: "Удалить из анкеты",
    TextKey.FIELD_DELETE_CONFIRM: "Удалить",
    TextKey.FIELD_DELETE_PROMPT: (
        "Удалить поле из этой анкеты? Оно не будет показываться в анкете, "
        "карточках и календаре. Данные останутся в базе."
    ),
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

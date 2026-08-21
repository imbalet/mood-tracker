from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    # Filling fields
    TextKey.SELECT_VALUE: "<b>{name}</b>\nВыбери значение.",
    TextKey.ENTER_TEXT: "<b>{name}</b>\nОтправь текст или пропусти этот шаг.",
    TextKey.BACK_TO_DAY: "← К записи дня",
    TextKey.REFERENCE_QUESTION: "Сегодня {adjective} твоего текущего рекордного дня?",
    TextKey.EMPTY_DAY: "Пока нет значений.",
    TextKey.EDIT_FIELD: "Изменить: {name}",
    TextKey.ADD_FIELD_VALUE: "Добавить: {name}",
    TextKey.DAY_DRAFT: "черновик",
    TextKey.DAY_COMPLETE: "завершён",
    TextKey.DAY_SKIPPED: "пропущено",
}

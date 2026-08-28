from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    # Filling fields
    TextKey.SELECT_VALUE: "<b>{name}</b>\nВыбери значение.",
    TextKey.ENTER_TEXT: "<b>{name}</b>\nОтправь текст или пропусти этот шаг.",
    TextKey.BACK_TO_DAY: "← К записи дня",
    TextKey.REFERENCE_QUESTION: "Сегодня {adjective} твоего текущего рекордного дня?",  # TODO: поменять  # noqa: E501
    TextKey.EMPTY_DAY: "Пока нет значений.",
    TextKey.EDIT_FIELD: "Изменить: {name}",
    TextKey.ADD_FIELD_VALUE: "Добавить: {name}",
    TextKey.DAY_DRAFT: "черновик",
    TextKey.DAY_COMPLETE: "завершён",
    TextKey.DAY_SKIPPED: "пропущено",
    # events
    TextKey.HOW_TO_CREATE_EVENT: "Как записать событие?",
    TextKey.FILL_QUESTIONNAIRE: "Заполнить анкету",
    TextKey.QUICK_TEXT: "Быстрый текст",
    TextKey.SEND_EVENT_TEXT: "Отправь текст события.",
    TextKey.SEND_NEW_TIME: "Отправь новое время в формате <code>ЧЧ:ММ</code>.",
    TextKey.INVALID_TIME_FORMAT: "Нужно время в формате <code>ЧЧ:ММ</code>.",
    TextKey.EMPTY_TEXT_ENTERED: "Отправь непустой текст",
    TextKey.EVENT_NOT_CREATED: "Событие не создано: ничего не заполнено.",
    TextKey.SEND_EVENT_TEXT_FIELD: "Отправь текст.",
    TextKey.CHOOSE_EVENT_VALUE_FIELD: "Выбери значение.",
    TextKey.DELETE_EVENT_CONFIRMATION: "Удалить событие?",
    TextKey.WHEN_EVENT_OCCURRED: "<b>Когда произошло событие?</b>",
    TextKey.EVENT_NOW_TIME: "Сейчас",
    TextKey.EVENT_SET_TIME: "Указать время",
    TextKey.EVENT_CONTINUE: "Продолжить",
    TextKey.EVENT_CHANGE_TIME: "Изменить время",
}

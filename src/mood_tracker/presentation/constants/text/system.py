from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    TextKey.START_FIRST: "Сначала создай дневник командой /start.",
    TextKey.ONBOARDING_GREETING: ("Привет!"),
    TextKey.STALE_BUTTON: "Кнопка устарела.",
    TextKey.OPERATION_FAILED: "Не удалось выполнить действие. Попробуй ещё раз позже.",
    TextKey.DAY_UNAVAILABLE: "Запись больше недоступна.",
    TextKey.TEXT_NOT_SAVED: (
        "Текст не сохранён. Отправь непустой текст или нажми «Пропустить»."
    ),
    TextKey.TEXT_SAVE_FAILED: (
        "Не удалось сохранить текст. Открой /today и попробуй ещё раз."
    ),
    TextKey.OPEN_TODAY_AGAIN: "Открой /today и попробуй ещё раз.",
    TextKey.FIELD_VALUE_UNAVAILABLE: (
        "Это значение больше недоступно. Открой /today заново."
    ),
    TextKey.FIELD_UNAVAILABLE: "Поле больше недоступно.",
    # Navigatione
    TextKey.BACK_TO_MENU: "🏠 В меню",
    TextKey.BACK: "← Назад",
    # Questionnaire navigation
    TextKey.SKIP: "Пропустить",
    TextKey.YES: "Да",
    TextKey.NO: "Нет",
}

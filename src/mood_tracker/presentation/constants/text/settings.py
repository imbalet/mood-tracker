from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    # Timezone
    TextKey.SELECT_TIMEZONE: "Выбери свой часовой пояс — по нему бот определяет дату записи и время напоминаний.",  # noqa: E501
    TextKey.ENTER_TIMEZONE: "Отправь IANA-имя, например <code>Asia/Tokyo</code>.",
    TextKey.INVALID_TIMEZONE: (
        "Не удалось распознать часовой пояс. Например: <code>Europe/Moscow</code>."
    ),
    TextKey.TIMEZONE_SAVED: "Готово! Часовой пояс: <b>{timezone}</b>.",
    TextKey.ANOTHER_TIMEZONE: "Другой часовой пояс",
}

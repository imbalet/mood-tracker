from ._key import TextKey

_TEXTS: dict[TextKey, str] = {
    TextKey.MENU_TITLE: "<b>Дневник состояния</b>\nВыбери, что хочешь сделать.",
    TextKey.MENU_TODAY: "📝 Сегодня",
    TextKey.MENU_DATES: "📆 Даты",
    TextKey.MENU_CALENDAR: "🗓 Календарь",
    TextKey.MENU_FIELDS: "⚙️ Поля",
    TextKey.MENU_SETTINGS: "Настройки",
    # calendar
    TextKey.MENU_CALENDAR_TITLE: "<b>Выбери дату</b>\n✅ — завершён, 📝 — черновик.",
}

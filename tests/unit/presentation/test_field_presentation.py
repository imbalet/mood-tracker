from mood_tracker.presentation.formatters import format_field_card
from mood_tracker.presentation.keyboards import (
    field_card_keyboard,
    field_order_keyboard,
    fields_keyboard,
)


def test_field_card_escapes_user_name(field_factory) -> None:
    field = field_factory.text(name="<важное>")

    rendered = format_field_card(field)

    assert "<b>&lt;важное&gt;</b>" in rendered


def test_fields_keyboard_exposes_each_field_and_navigation(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    markup = fields_keyboard((first, second))

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["Первое"],
        ["Второе"],
        ["＋ Добавить поле"],
        ["Изменить порядок"],
        ["🏠 В меню"],
    ]


def test_core_field_keyboard_does_not_offer_status_changes(field_factory) -> None:
    field = field_factory.scale(is_core=True)

    markup = field_card_keyboard(field)
    texts = {button.text for row in markup.inline_keyboard for button in row}

    assert "Активно" not in texts
    assert "Неактивно" not in texts
    assert "Скрыто" not in texts
    assert "Палитра состояния" in texts


def test_first_ordered_field_has_no_up_button(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    markup = field_order_keyboard((first, second), first.id)
    texts = {button.text for row in markup.inline_keyboard for button in row}

    assert "↑ Выше" not in texts
    assert "↓ Ниже" in texts

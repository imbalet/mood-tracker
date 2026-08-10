from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireFieldRole
from mood_tracker.presentation.screens import (
    field_card_screen,
    field_order_screen,
    fields_list_screen,
)
from mood_tracker.presentation.view_models import (
    make_field_card_view,
    make_field_order_view,
    make_fields_list_view,
)


def test_field_card_escapes_user_name(field_factory) -> None:
    field = field_factory.text(name="<важное>")

    screen = field_card_screen(
        make_field_card_view(
            field,
            QuestionnaireField(field.id, 0, role=QuestionnaireFieldRole.DAY_STATE),
        )
    )

    assert isinstance(screen.content, str)
    assert "<b>&lt;важное&gt;</b>" in screen.content


def test_fields_keyboard_exposes_each_field_and_navigation(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    screen = fields_list_screen(make_fields_list_view((first, second)))

    assert screen.reply_markup is not None
    assert [
        [button.text for button in row] for row in screen.reply_markup.inline_keyboard
    ] == [
        ["Первое"],
        ["Второе"],
        ["＋ Добавить поле"],
        ["Добавить из другой анкеты"],
        ["Изменить порядок"],
        ["🏠 В меню"],
    ]


def test_core_field_keyboard_does_not_offer_status_changes(field_factory) -> None:
    field = field_factory.scale(is_core=True)

    screen = field_card_screen(
        make_field_card_view(
            field,
            QuestionnaireField(field.id, 0, role=QuestionnaireFieldRole.DAY_STATE),
        )
    )
    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }

    assert "Активно" not in texts
    assert "Неактивно" not in texts
    assert "Скрыто" not in texts
    assert "Палитра состояния" in texts


def test_ordinary_field_keyboard_exposes_enablement_and_soft_delete(
    field_factory,
) -> None:
    field = field_factory.text()

    screen = field_card_screen(
        make_field_card_view(field, QuestionnaireField(field.id, 0))
    )

    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }
    assert "Отключить в анкете" in texts
    assert "Удалить поле" in texts
    assert "Скрыто" not in texts


def test_disabled_field_keyboard_offers_reenable(field_factory) -> None:
    field = field_factory.text()

    screen = field_card_screen(
        make_field_card_view(field, QuestionnaireField(field.id, 0, is_enabled=False))
    )

    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }
    assert "Включить в анкете" in texts


def test_first_ordered_field_has_no_up_button(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    screen = field_order_screen(make_field_order_view((first, second), first.id))
    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }

    assert "↑ Выше" not in texts
    assert "↓ Ниже" in texts

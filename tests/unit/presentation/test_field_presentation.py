from mood_tracker.application.contracts.questionnaires import QuestionnaireFieldItem
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import QuestionnaireFieldRole, QuestionnaireKind
from mood_tracker.presentation.screens.fields import (
    FieldCardScreen,
    FieldListScreen,
    FieldOrderScreen,
)
from mood_tracker.presentation.view_models import (
    make_field_card_view,
    make_field_order_view,
)


def test_field_card_escapes_user_name(field_factory) -> None:
    field = field_factory.text(name="<важное>")

    screen = FieldCardScreen(
        make_field_card_view(
            field,
            QuestionnaireField(field.id, 0, role=QuestionnaireFieldRole.DAY_STATE),
        )
    ).render()

    assert isinstance(screen.content, str)
    assert "<b>&lt;важное&gt;</b>" in screen.content


def test_fields_keyboard_exposes_each_field_and_navigation(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    screen = FieldListScreen(
        items=(
            QuestionnaireFieldItem(first, QuestionnaireField(first.id, 0)),
            QuestionnaireFieldItem(second, QuestionnaireField(second.id, 1)),
        ),
        kind=QuestionnaireKind.DAY,
    ).render()

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

    screen = FieldCardScreen(
        make_field_card_view(
            field,
            QuestionnaireField(field.id, 0, role=QuestionnaireFieldRole.DAY_STATE),
        )
    ).render()
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

    screen = FieldCardScreen(
        make_field_card_view(field, QuestionnaireField(field.id, 0))
    ).render()

    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }
    assert "Отключить в анкете" in texts
    assert "Удалить из анкеты" in texts
    assert "Скрыто" not in texts


def test_disabled_field_keyboard_offers_reenable(field_factory) -> None:
    field = field_factory.text()

    screen = FieldCardScreen(
        make_field_card_view(field, QuestionnaireField(field.id, 0, is_enabled=False))
    ).render()

    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }
    assert "Включить в анкете" in texts


def test_first_ordered_field_has_no_up_button(field_factory) -> None:
    first = field_factory.text(name="Первое")
    second = field_factory.text(name="Второе")

    screen = FieldOrderScreen(make_field_order_view((first, second), first.id)).render()
    assert screen.reply_markup is not None
    texts = {
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    }

    assert "↑ Выше" not in texts
    assert "↓ Ниже" in texts

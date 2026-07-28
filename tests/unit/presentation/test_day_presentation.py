from mood_tracker.application.commands import DayForm
from mood_tracker.domain.entities import DayFieldProgress
from mood_tracker.domain.enums import DayStatus
from mood_tracker.presentation.formatters import format_day_card
from mood_tracker.presentation.keyboards import day_edit_keyboard


def test_day_card_shows_saved_values_skips_and_current_prompt(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(name="Состояние", is_core=True)
    comment = field_factory.text(name="Комментарий", sort_order=1)
    day = day_factory.build()
    day.save_value(state.current_version, 6)
    day.skip_text(comment.current_version)
    form = DayForm(day.date, day, (state, comment), next_field=None)

    rendered = format_day_card(form, "<b>Плач</b>\nВыбери значение.")

    assert "черновик" in rendered
    assert "<b>Состояние</b>: 6/10" in rendered
    assert "<b>Комментарий</b>: пропущено" in rendered
    assert rendered.endswith("<b>Плач</b>\nВыбери значение.")


def test_day_card_keyboard_allows_editing_and_adding_current_active_fields(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(name="Состояние", is_core=True)
    crying = field_factory.ordinal(name="Плач", sort_order=1)
    day = day_factory.build(
        status=DayStatus.COMPLETE,
        progress={
            state.id: DayFieldProgress(
                field_id=state.id,
                field_version_id=state.current_version.id,
                skipped=False,
            )
        },
    )
    form = DayForm(day.date, day, (state, crying), next_field=None)

    markup = day_edit_keyboard(form)

    assert [[button.text for button in row] for row in markup.inline_keyboard] == [
        ["Изменить: Состояние"],
        ["Добавить: Плач"],
        ["🏠 В меню"],
    ]

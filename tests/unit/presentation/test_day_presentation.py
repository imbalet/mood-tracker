from uuid import uuid7

from mood_tracker.application.commands import DayForm
from mood_tracker.domain.entities import (
    DayFieldProgress,
    DayValue,
    FieldVersion,
    OrdinalConfig,
    OrdinalOption,
)
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.domain.enums import DayStatus, FieldType
from mood_tracker.presentation.screens import day_card_screen, day_value_prompt_screen
from mood_tracker.presentation.view_models import (
    make_day_card_view,
    make_day_value_prompt_view,
)


def test_day_card_shows_saved_values_skips_and_current_prompt(
    day_factory, field_factory
) -> None:
    state = field_factory.scale(name="Состояние", is_core=True)
    comment = field_factory.text(name="Комментарий", sort_order=1)
    day = day_factory.build()
    day.save_value(state.current_version, 6)
    day.skip_text(comment.current_version)
    form = DayForm(day.date, day, (state, comment), next_field=None)

    screen = day_value_prompt_screen(make_day_value_prompt_view(form, state))

    assert isinstance(screen.content, str)
    assert "черновик" in screen.content
    assert "<b>Состояние</b>: 6/10" in screen.content
    assert "<b>Комментарий</b>: пропущено" in screen.content
    assert screen.content.endswith("<b>Состояние</b>\nВыбери значение.")


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
    form = DayForm(
        day.date,
        day,
        (state, crying),
        next_field=None,
        placements={
            state.id: QuestionnaireField(state.id, 0),
            crying.id: QuestionnaireField(crying.id, 1),
        },
    )

    screen = day_card_screen(make_day_card_view(form))

    assert screen.reply_markup is not None
    assert [
        [button.text for button in row] for row in screen.reply_markup.inline_keyboard
    ] == [
        ["Изменить: Состояние"],
        ["Добавить: Плач"],
        ["＋ Добавить событие"],
        ["🏠 В меню"],
    ]


def test_day_view_uses_the_saved_ordinal_version(day_factory, field_factory) -> None:
    field = field_factory.ordinal(
        options=(OrdinalOption(0, "Нет"), OrdinalOption(1, "Да"))
    )
    previous_version = field.current_version
    field.add_version(
        FieldVersion(
            id=uuid7(),
            field_id=field.id,
            type=FieldType.ORDINAL,
            config=OrdinalConfig(
                (
                    OrdinalOption(0, "Нет"),
                    OrdinalOption(1, "Немного"),
                    OrdinalOption(2, "Много"),
                )
            ),
            created_at=field.current_version.created_at,
        )
    )
    day = day_factory.build()
    day.values[field.id] = DayValue(
        day_id=day.id,
        field_id=field.id,
        field_version_id=previous_version.id,
        value=1,
        normalized_value=1.0,
    )
    day.progress[field.id] = DayFieldProgress(
        field_id=field.id,
        field_version_id=previous_version.id,
        skipped=False,
    )
    view = make_day_card_view(
        DayForm(
            day.date,
            day,
            (field,),
            next_field=None,
            placements={field.id: QuestionnaireField(field.id, 0, is_enabled=False)},
        )
    )

    assert view.entries[0].rendered_value == "Да"
    assert view.actions[0].action.value == "edit"

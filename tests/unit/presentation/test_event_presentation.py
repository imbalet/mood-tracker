from mood_tracker.application.contracts.questionnaires import QuestionnaireFieldItem
from mood_tracker.domain.entities.questionnaire import QuestionnaireField
from mood_tracker.presentation.screens.events import PromptValueScreen

# TODO: посмотреть слоп


def test_required_scale_event_prompt_contains_value_buttons(field_factory) -> None:
    field = field_factory.scale(minimum=1, maximum=3)
    item = QuestionnaireFieldItem(field, QuestionnaireField(field.id, 0))

    screen = PromptValueScreen(item=item, event_id=field.id).render()

    assert screen.reply_markup is not None
    assert [
        [button.text for button in row] for row in screen.reply_markup.inline_keyboard
    ] == [
        ["1"],
        ["2"],
        ["3"],
    ]

from mood_tracker.domain.entities import FieldDisplayConfig, StatePalette
from mood_tracker.presentation.screens import palette_screen
from mood_tracker.presentation.view_models import make_palette_view


def test_palette_screen_embeds_numbered_preview(field_factory) -> None:
    palette = StatePalette("#112233", "#445566", "#778899")
    field = field_factory.scale(
        is_core=True,
        display_config=FieldDisplayConfig(state_palette=palette),
    )

    view = make_palette_view(field)
    assert view is not None
    screen = palette_screen(view)

    assert screen.content.html and screen.content.media
    assert 'src="tg://photo?id=scale"' in screen.content.html
    assert screen.content.media[0].id == "scale"
    assert "#112233 → #445566 → #778899" in screen.content.html

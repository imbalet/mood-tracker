"""Built-in visual palettes for the core state field."""

from mood_tracker.domain.entities import StatePalette
from mood_tracker.presentation.callbacks.callbacks import PalettePreset

PALETTES: dict[PalettePreset, StatePalette] = {
    PalettePreset.WARM: StatePalette("#D9534F", "#F0E68C", "#5CB85C"),
    PalettePreset.FOREST: StatePalette("#8D6E63", "#C5E1A5", "#2E7D32"),
    PalettePreset.COOL: StatePalette("#3A0CA3", "#4CC9F0", "#2A9D8F"),
}

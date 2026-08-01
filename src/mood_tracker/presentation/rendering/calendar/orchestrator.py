from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class VisualizationKind(StrEnum):
    MONTH_CALENDAR = "month_calendar"


@dataclass(frozen=True, slots=True)
class RenderedImage:
    data: bytes
    filename: str
    media_type: str = "image/png"


class RenderRequest(Protocol):
    @property
    def kind(self) -> VisualizationKind: ...


class Visualization(Protocol):
    kind: VisualizationKind

    def render(self, request: object) -> RenderedImage: ...


class RenderOrchestrator:
    """Registry for visualizations with different input DTOs.

    The orchestrator only selects a visualization. Domain-to-visual mapping stays
    beside the concrete visualization, so adding a year graph does not grow this
    class or require it to understand that graph's request model.
    """

    def __init__(self, visualizations: Iterable[Visualization]) -> None:
        self._visualizations = {item.kind: item for item in visualizations}

    def render(self, request: RenderRequest) -> RenderedImage:
        try:
            visualization = self._visualizations[request.kind]
        except KeyError as error:
            raise ValueError(f"Unsupported visualization: {request.kind}") from error
        return visualization.render(request)

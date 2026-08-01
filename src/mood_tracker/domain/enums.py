"""Enumerations shared by domain models."""

from enum import StrEnum


class FieldType(StrEnum):
    """The semantic type of a field version."""

    SCALE = "scale"
    ORDINAL = "ordinal"
    TEXT = "text"


class FieldStatus(StrEnum):
    """The current visibility and input lifecycle of a field."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    HIDDEN = "hidden"


class DayStatus(StrEnum):
    """The historical completion state of a day."""

    DRAFT = "draft"
    COMPLETE = "complete"


class EventStatus(StrEnum):
    """Lifecycle of an event questionnaire."""

    DRAFT = "draft"
    COMPLETE = "complete"


class ReferenceType(StrEnum):
    """The direction of a personal best/worst reference day."""

    BEST = "best"
    WORST = "worst"

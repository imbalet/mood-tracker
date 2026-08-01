"""Errors raised by application use cases."""


class ApplicationError(Exception):
    """Base error that presentation can map to user-facing feedback."""


class UserNotFound(ApplicationError):
    """Raised when an operation addresses no accessible user profile."""


class FieldNotFound(ApplicationError):
    """Raised when an operation addresses no accessible field."""


class DayNotFound(ApplicationError):
    """Raised when an operation addresses no accessible day."""


class EventNotFound(ApplicationError):
    """Raised when an operation addresses no accessible event."""


class IdentifierCollision(ApplicationError):
    """Raised by persistence when a generated UUID collides with an existing ID."""


class IdentifierGenerationExhausted(ApplicationError):
    """Raised after all retry attempts for a generated UUID collision fail."""

"""Domain-specific errors raised when an invariant is violated."""


class DomainError(Exception):
    """Base class for errors that presentation can map to user feedback."""


class InvalidTimezone(DomainError):
    """Raised when a timezone is not a valid IANA timezone name."""


class InvalidFieldVersion(DomainError):
    """Raised when a field version or its configuration is invalid."""


class InvalidFieldValue(DomainError):
    """Raised when a value does not conform to its field version."""


class CoreFieldViolation(DomainError):
    """Raised when an operation would violate the state-field invariant."""


class QuestionnaireViolation(DomainError):
    """Raised when an operation violates questionnaire placement rules."""


class IncompleteDay(DomainError):
    """Raised when attempting to complete a day with unfinished active fields."""


class ReferenceDayViolation(DomainError):
    """Raised when an operation contradicts the reference-day history."""

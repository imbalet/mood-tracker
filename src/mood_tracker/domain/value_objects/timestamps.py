"""Validation helpers for timestamps stored by the domain."""

from datetime import UTC, datetime, timedelta

from mood_tracker.domain.errors import InvalidTimestamp


def require_utc(value: datetime, label: str) -> datetime:
    """Return an aware UTC timestamp or reject a value outside the invariant."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidTimestamp(f"{label} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise InvalidTimestamp(f"{label} must be expressed in UTC")
    return value.astimezone(UTC)

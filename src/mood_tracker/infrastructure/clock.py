"""Production clock adapter."""

from datetime import UTC, datetime


class SystemClock:
    """Return the current UTC time from the system clock."""

    def now(self) -> datetime:
        """Return a timezone-aware UTC timestamp."""
        return datetime.now(UTC)

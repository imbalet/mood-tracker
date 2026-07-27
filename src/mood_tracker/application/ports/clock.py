"""Clock boundary for deterministic application time."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provide the current timezone-aware UTC timestamp."""

    def now(self) -> datetime:
        """Return the current instant."""

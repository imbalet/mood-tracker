"""Timezone value object."""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mood_tracker.domain.errors import InvalidTimezone
from mood_tracker.domain.value_objects.timestamps import require_utc


@dataclass(frozen=True, slots=True)
class UserTimezone:
    """A validated IANA timezone name used for user-local calendar dates."""

    name: str

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.name)
        except ZoneInfoNotFoundError as error:
            msg = f"Unknown IANA timezone: {self.name}"
            raise InvalidTimezone(msg) from error

    def local_date_at(self, instant: datetime) -> date:
        """Return this timezone's calendar date for a UTC instant."""
        instant = require_utc(instant, "Local-date instant")
        return instant.astimezone(ZoneInfo(self.name)).date()

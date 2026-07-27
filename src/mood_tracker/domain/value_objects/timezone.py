"""Timezone value object."""

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mood_tracker.domain.errors import InvalidTimezone


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

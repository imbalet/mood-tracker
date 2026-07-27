"""Rules for turning a draft day into a historically complete day."""

from collections.abc import Iterable
from datetime import datetime

from mood_tracker.domain.entities.day import Day
from mood_tracker.domain.entities.field import Field
from mood_tracker.domain.errors import IncompleteDay


class CompletionPolicy:
    """Check active field steps without coupling Day to field persistence."""

    def complete(
        self, day: Day, fields: Iterable[Field], completed_at: datetime
    ) -> None:
        """Complete a day only when every supplied active field has progress."""
        missing_ids = [
            field.id
            for field in fields
            if field.is_active and not day.has_completed_step(field.id)
        ]
        if missing_ids:
            msg = f"Day has {len(missing_ids)} unfinished active field(s)"
            raise IncompleteDay(msg)
        day.complete(completed_at)

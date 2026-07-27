"""Standard-library UUIDv7 generator adapter."""

from uuid import UUID, uuid7


class Uuid7IdGenerator:
    """Generate sortable UUIDv7 identifiers for application entities."""

    def new(self) -> UUID:
        """Return a new UUIDv7."""
        return uuid7()

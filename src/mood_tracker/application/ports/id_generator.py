"""Identifier generator boundary."""

from typing import Protocol
from uuid import UUID


class IdGenerator(Protocol):
    """Generate new internal entity identifiers."""

    def new(self) -> UUID:
        """Return a fresh identifier."""
        ...

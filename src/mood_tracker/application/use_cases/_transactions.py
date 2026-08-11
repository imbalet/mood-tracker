"""Shared retry behavior for write use cases."""

from collections.abc import Awaitable, Callable

from mood_tracker.application.errors import (
    IdentifierCollision,
    IdentifierGenerationExhausted,
)
from mood_tracker.application.ports import UnitOfWork

MAX_IDENTIFIER_ATTEMPTS = 3


async def execute_transaction[ResultT](
    uow: UnitOfWork, operation: Callable[[], Awaitable[ResultT]]
) -> ResultT:
    """Commit one write operation without retrying identifier generation."""
    async with uow:
        result = await operation()
        await uow.commit()
        return result


async def execute_write[ResultT](
    uow: UnitOfWork, operation: Callable[[], Awaitable[ResultT]]
) -> ResultT:
    """Commit a write and retry the whole operation after an ID collision."""
    for attempt in range(MAX_IDENTIFIER_ATTEMPTS):
        try:
            async with uow:
                result = await operation()
                await uow.commit()
                return result
        except IdentifierCollision:
            # TODO: add logging
            if attempt == MAX_IDENTIFIER_ATTEMPTS - 1:
                raise IdentifierGenerationExhausted from None
    raise AssertionError("Identifier retry loop must return or raise")

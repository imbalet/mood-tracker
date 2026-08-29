"""Background loop for processing user-local reminders."""

# TODO: посмотреть слоп

import asyncio
import contextlib
import logging

from mood_tracker.presentation.services import ApplicationServices
from mood_tracker.presentation.utils.sender import Sender

logger = logging.getLogger(__name__)


class ReminderWorker:
    """Periodically process reminders for every registered user."""

    def __init__(
        self, services: ApplicationServices, sender: Sender, interval: float
    ) -> None:
        self._services = services
        self._sender = sender
        self._interval = interval

    async def run(self) -> None:
        """Run until cancelled, isolating failures to individual users."""
        while True:
            await self._process_once()
            await asyncio.sleep(self._interval)

    async def _process_once(self) -> None:
        try:
            user_ids = await self._services.list_user_ids()
        except Exception:
            logger.exception("Failed to load users for reminder processing")
            return
        for user_id in user_ids:
            try:
                await self._services.process_reminder(self._sender).execute(user_id)
            except Exception:
                logger.exception("Failed to process reminder for user %s", user_id)


async def stop_reminder_worker(task: asyncio.Task[None]) -> None:
    """Cancel a reminder worker and wait until its resources are released."""
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

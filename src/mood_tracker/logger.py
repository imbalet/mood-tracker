from __future__ import annotations

import logging
import sys


def setup_logging(level: str) -> None:
    """Configure concise process logging for containers and local development."""
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )

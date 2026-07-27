from __future__ import annotations

import asyncio

from aiohttp import web


async def health(_: web.Request) -> web.Response:
    """Return a minimal liveness response for Docker."""
    return web.json_response({"status": "ok"})


async def start_healthcheck_server(port: int) -> None:
    """Start the local HTTP liveness server until the task is cancelled."""
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)  # noqa: S104
    await site.start()
    try:
        await asyncio.Future[None]()
    finally:
        await runner.cleanup()

import asyncio
import logging
from datetime import timedelta

from app.db.base import async_session_maker
from app.telegram.client_pool import pool
from app.telegram.health_check import check_all_accounts

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def _loop(interval_seconds: float, idle_timeout: timedelta) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with async_session_maker() as db:
                await check_all_accounts(db)
            await pool.disconnect_idle(idle_timeout)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background health-check loop failed")


def start(interval_seconds: float, idle_timeout_minutes: float) -> None:
    global _task
    _task = asyncio.create_task(_loop(interval_seconds, timedelta(minutes=idle_timeout_minutes)))


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
        _task = None

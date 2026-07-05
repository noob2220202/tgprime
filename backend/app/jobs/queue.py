import asyncio
import logging

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[str] = asyncio.Queue()
_workers: list[asyncio.Task] = []


async def enqueue(item_id: str) -> None:
    await _queue.put(item_id)


def schedule_retry(item_id: str, delay_seconds: float) -> None:
    """Re-enqueues item_id after delay_seconds without busy-retrying — used
    for FloodWait backoff and cooldown deferrals."""
    loop = asyncio.get_event_loop()
    loop.call_later(max(delay_seconds, 0), lambda: asyncio.ensure_future(enqueue(item_id)))


async def _worker_loop(worker_id: int) -> None:
    from app.jobs.profile_update import process_item

    while True:
        item_id = await _queue.get()
        try:
            await process_item(item_id)
        except Exception:
            logger.exception("Unhandled error processing bulk job item %s", item_id)
        finally:
            _queue.task_done()


def start_workers(count: int) -> None:
    global _workers
    _workers = [asyncio.create_task(_worker_loop(i)) for i in range(count)]


async def stop_workers() -> None:
    for task in _workers:
        task.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)
    _workers.clear()


async def recover_pending_items() -> None:
    """On startup, re-enqueue items left mid-flight by a previous process
    exit (no Redis/arq persistence, so this is the recovery mechanism)."""
    from sqlalchemy import select

    from app.db.base import async_session_maker
    from app.db.models import BulkJobItem

    async with async_session_maker() as db:
        result = await db.execute(
            select(BulkJobItem.id).where(BulkJobItem.status.in_(["pending", "running", "skipped_flood_wait"]))
        )
        item_ids = [row[0] for row in result.all()]

    for item_id in item_ids:
        await enqueue(item_id)

import asyncio
import base64
import random
from datetime import datetime, timedelta

from telethon.errors import FloodWaitError, PeerFloodError, RPCError

from app.config import get_settings
from app.db.base import async_session_maker
from app.db.models import BulkJob, BulkJobItem, TelegramAccount
from app.jobs.queue import schedule_retry
from app.telegram import profile_ops
from app.telegram.client_pool import pool
from app.telegram.crypto import decrypt

FLOOD_WAIT_BUFFER_SECONDS = 5


def _resolve_fields(job: BulkJob, item: BulkJobItem) -> dict:
    fields = dict(job.payload_template or {})
    if item.payload_override:
        fields.update(item.payload_override)
    return fields


async def _finish_job_if_complete(db, job: BulkJob) -> None:
    if job.status == "paused_flood":
        return
    done_count = job.succeeded_count + job.failed_count
    if done_count >= job.total_items:
        job.status = "completed" if job.failed_count == 0 else "completed_with_errors"
        job.finished_at = datetime.utcnow()


async def process_item(item_id: str) -> None:
    settings = get_settings()

    async with async_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        if item is None or item.status not in ("pending", "skipped_flood_wait"):
            return

        job = await db.get(BulkJob, item.job_id)
        if job is None:
            return

        if job.status == "paused_flood":
            # Circuit breaker tripped by another item in this job — leave the
            # rest for manual review rather than silently continuing.
            item.status = "failed"
            item.error_message = "다른 계정에서 PeerFloodError가 발생해 작업이 일시중단됐습니다. 확인 후 다시 시도하세요."
            item.finished_at = datetime.utcnow()
            job.failed_count += 1
            await db.commit()
            return

        account = await db.get(TelegramAccount, item.account_id)
        if account is None:
            item.status = "failed"
            item.error_message = "계정을 찾을 수 없습니다."
            item.finished_at = datetime.utcnow()
            job.failed_count += 1
            await _finish_job_if_complete(db, job)
            await db.commit()
            return

        if account.status in ("banned", "frozen"):
            item.status = "failed"
            item.error_message = f"계정이 {account.status} 상태라 건너뜁니다."
            item.finished_at = datetime.utcnow()
            job.failed_count += 1
            await _finish_job_if_complete(db, job)
            await db.commit()
            return

        now = datetime.utcnow()

        if account.flood_wait_until and account.flood_wait_until > now:
            remaining = (account.flood_wait_until - now).total_seconds()
            await db.commit()
            schedule_retry(item_id, remaining + FLOOD_WAIT_BUFFER_SECONDS)
            return

        cooldown = timedelta(minutes=settings.profile_edit_min_cooldown_minutes)
        if account.last_profile_edit_at and now - account.last_profile_edit_at < cooldown:
            remaining = (cooldown - (now - account.last_profile_edit_at)).total_seconds()
            await db.commit()
            schedule_retry(item_id, remaining)
            return

        item.status = "running"
        item.attempt_count += 1
        item.started_at = now
        job.status = "running" if job.status == "pending" else job.status
        job.started_at = job.started_at or now
        await db.commit()

        fields = _resolve_fields(job, item)
        account_id = account.id
        api_id = account.api_id
        api_hash = decrypt(account.api_hash_encrypted)
        session_str = decrypt(account.session_encrypted)

    # Jitter delay happens outside the DB transaction so we don't hold a
    # connection open while sleeping.
    await asyncio.sleep(random.uniform(settings.profile_edit_min_jitter_seconds, settings.profile_edit_max_jitter_seconds))

    try:
        async with pool.lock(account_id):
            client = await pool.get_or_connect(account_id, api_id, api_hash, session_str)

            if any(k in fields for k in ("first_name", "last_name", "bio")):
                await profile_ops.update_profile(
                    client,
                    first_name=fields.get("first_name"),
                    last_name=fields.get("last_name"),
                    about=fields.get("bio"),
                )
            if "username" in fields and fields["username"]:
                await profile_ops.update_username(client, fields["username"])
            if "photo_base64" in fields and fields["photo_base64"]:
                await profile_ops.update_profile_photo(client, base64.b64decode(fields["photo_base64"]))
    except FloodWaitError as e:
        async with async_session_maker() as db:
            item = await db.get(BulkJobItem, item_id)
            account = await db.get(TelegramAccount, account_id)
            item.status = "skipped_flood_wait"
            item.flood_wait_seconds = e.seconds
            item.finished_at = datetime.utcnow()
            account.status = "flood_wait"
            account.flood_wait_until = datetime.utcnow() + timedelta(seconds=e.seconds)
            await db.commit()
        schedule_retry(item_id, e.seconds + FLOOD_WAIT_BUFFER_SECONDS)
        return
    except PeerFloodError as e:
        async with async_session_maker() as db:
            item = await db.get(BulkJobItem, item_id)
            job = await db.get(BulkJob, item.job_id)
            account = await db.get(TelegramAccount, account_id)
            item.status = "failed"
            item.error_message = f"PeerFloodError: {e}"
            item.finished_at = datetime.utcnow()
            account.status = "error"
            account.status_detail = "PeerFloodError — 계정이 스팸으로 플래그됐을 수 있습니다."
            job.status = "paused_flood"
            job.failed_count += 1
            await db.commit()
        return
    except RPCError as e:
        async with async_session_maker() as db:
            item = await db.get(BulkJobItem, item_id)
            job = await db.get(BulkJob, item.job_id)
            item.status = "failed"
            item.error_message = str(e)
            item.finished_at = datetime.utcnow()
            job.failed_count += 1
            await _finish_job_if_complete(db, job)
            await db.commit()
        return

    async with async_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        job = await db.get(BulkJob, item.job_id)
        account = await db.get(TelegramAccount, account_id)

        item.status = "succeeded"
        item.finished_at = datetime.utcnow()
        job.succeeded_count += 1

        account.last_profile_edit_at = datetime.utcnow()
        account.status = "active"
        if "first_name" in fields:
            account.first_name = fields["first_name"]
        if "last_name" in fields:
            account.last_name = fields["last_name"]
        if "bio" in fields:
            account.bio = fields["bio"]
        if "username" in fields and fields["username"]:
            account.username = fields["username"]

        await _finish_job_if_complete(db, job)
        await db.commit()

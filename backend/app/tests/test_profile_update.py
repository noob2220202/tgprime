from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from telethon.errors import FloodWaitError, PeerFloodError

from app.db.base import Base
from app.db.models import BulkJob, BulkJobItem, TelegramAccount
from app.jobs import profile_update
from app.telegram.client_pool import InvalidSessionError
from app.telegram.crypto import encrypt


@dataclass
class FakeSettings:
    profile_edit_min_jitter_seconds: float = 0
    profile_edit_max_jitter_seconds: float = 0
    profile_edit_min_cooldown_minutes: int = 30


@pytest_asyncio.fixture
async def job_session_maker(monkeypatch):
    # StaticPool keeps every checkout on the same in-memory connection, so
    # process_item's several independent `async with async_session_maker()`
    # blocks all see the same data (unlike the default per-checkout behavior).
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(profile_update, "async_session_maker", session_maker)
    monkeypatch.setattr(profile_update, "get_settings", lambda: FakeSettings())

    yield session_maker

    await engine.dispose()


async def _make_job_and_item(session_maker, *, account_overrides: dict | None = None, job_fields: dict | None = None):
    async with session_maker() as db:
        account = TelegramAccount(
            label="Test",
            api_id=1,
            api_hash_encrypted=encrypt("hash"),
            session_encrypted=encrypt("session"),
            status="active",
            **(account_overrides or {}),
        )
        db.add(account)
        await db.flush()

        job = BulkJob(
            job_type="bulk_profile_update",
            status="pending",
            payload_template=job_fields or {"first_name": "NewName", "bio": "NewBio"},
            total_items=1,
        )
        db.add(job)
        await db.flush()

        item = BulkJobItem(job_id=job.id, account_id=account.id, status="pending")
        db.add(item)
        await db.commit()
        await db.refresh(account)
        await db.refresh(job)
        await db.refresh(item)
        return account.id, job.id, item.id


@pytest.mark.asyncio
async def test_successful_update_marks_item_succeeded_and_completes_job(job_session_maker, monkeypatch):
    account_id, job_id, item_id = await _make_job_and_item(job_session_maker)

    calls = {}

    async def fake_update_profile(client, **kwargs):
        calls["update_profile"] = kwargs

    monkeypatch.setattr(profile_update.profile_ops, "update_profile", fake_update_profile)
    monkeypatch.setattr(profile_update.pool, "get_or_connect", lambda *a, **k: _async_return(object()))

    await profile_update.process_item(item_id)

    async with job_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        job = await db.get(BulkJob, job_id)
        account = await db.get(TelegramAccount, account_id)

    assert item.status == "succeeded"
    assert job.status == "completed"
    assert job.succeeded_count == 1
    assert account.first_name == "NewName"
    assert account.bio == "NewBio"
    assert account.last_profile_edit_at is not None
    assert calls["update_profile"] == {"first_name": "NewName", "last_name": None, "about": "NewBio"}


@pytest.mark.asyncio
async def test_flood_wait_defers_item_without_marking_failed(job_session_maker, monkeypatch):
    account_id, job_id, item_id = await _make_job_and_item(job_session_maker)

    async def raise_flood_wait(client, **kwargs):
        raise FloodWaitError(request=None, capture=30)

    retries = []
    monkeypatch.setattr(profile_update.profile_ops, "update_profile", raise_flood_wait)
    monkeypatch.setattr(profile_update.pool, "get_or_connect", lambda *a, **k: _async_return(object()))
    monkeypatch.setattr(profile_update, "schedule_retry", lambda item_id, delay: retries.append((item_id, delay)))

    await profile_update.process_item(item_id)

    async with job_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        account = await db.get(TelegramAccount, account_id)

    assert item.status == "skipped_flood_wait"
    assert item.flood_wait_seconds == 30
    assert account.status == "flood_wait"
    assert account.flood_wait_until is not None
    assert retries == [(item_id, 30 + profile_update.FLOOD_WAIT_BUFFER_SECONDS)]


@pytest.mark.asyncio
async def test_peer_flood_pauses_job_for_remaining_items(job_session_maker, monkeypatch):
    account_id, job_id, item_id = await _make_job_and_item(job_session_maker)

    async def raise_peer_flood(client, **kwargs):
        raise PeerFloodError(request=None)

    monkeypatch.setattr(profile_update.profile_ops, "update_profile", raise_peer_flood)
    monkeypatch.setattr(profile_update.pool, "get_or_connect", lambda *a, **k: _async_return(object()))

    await profile_update.process_item(item_id)

    async with job_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        job = await db.get(BulkJob, job_id)
        account = await db.get(TelegramAccount, account_id)

    assert item.status == "failed"
    assert job.status == "paused_flood"
    assert account.status == "error"

    # A second item queued under the same paused job must not be processed further.
    async with job_session_maker() as db:
        second_item = BulkJobItem(job_id=job_id, account_id=account_id, status="pending")
        db.add(second_item)
        await db.commit()
        await db.refresh(second_item)
        second_item_id = second_item.id

    await profile_update.process_item(second_item_id)

    async with job_session_maker() as db:
        second_item = await db.get(BulkJobItem, second_item_id)
    assert second_item.status == "failed"
    assert "일시중단" in second_item.error_message


@pytest.mark.asyncio
async def test_corrupt_session_marks_item_and_account_failed(job_session_maker, monkeypatch):
    account_id, job_id, item_id = await _make_job_and_item(job_session_maker)

    async def raise_invalid_session(*a, **k):
        raise InvalidSessionError("세션에 연결할 수 없습니다: Not a valid string")

    monkeypatch.setattr(profile_update.pool, "get_or_connect", raise_invalid_session)

    await profile_update.process_item(item_id)

    async with job_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
        job = await db.get(BulkJob, job_id)
        account = await db.get(TelegramAccount, account_id)

    assert item.status == "failed"
    assert "세션에 연결할 수 없습니다" in item.error_message
    assert account.status == "error"
    assert job.status == "completed_with_errors"


@pytest.mark.asyncio
async def test_cooldown_defers_without_calling_telethon(job_session_maker, monkeypatch):
    account_id, job_id, item_id = await _make_job_and_item(
        job_session_maker, account_overrides={"last_profile_edit_at": datetime.utcnow()}
    )

    called = False

    async def fake_update_profile(client, **kwargs):
        nonlocal called
        called = True

    retries = []
    monkeypatch.setattr(profile_update.profile_ops, "update_profile", fake_update_profile)
    monkeypatch.setattr(profile_update, "schedule_retry", lambda item_id, delay: retries.append((item_id, delay)))

    await profile_update.process_item(item_id)

    assert called is False
    assert len(retries) == 1
    assert retries[0][0] == item_id

    async with job_session_maker() as db:
        item = await db.get(BulkJobItem, item_id)
    assert item.status == "pending"


async def _async_return(value):
    return value

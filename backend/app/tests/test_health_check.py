from datetime import datetime, timedelta

import pytest
from telethon.errors import AuthKeyUnregisteredError, UserDeactivatedBanError

from app.db.models import TelegramAccount
from app.telegram import health_check
from app.telegram.crypto import encrypt


def _make_account(**overrides) -> TelegramAccount:
    defaults = {
        "label": "Test",
        "api_id": 1,
        "api_hash_encrypted": encrypt("hash"),
        "session_encrypted": encrypt("session"),
        "status": "active",
    }
    defaults.update(overrides)
    return TelegramAccount(**defaults)


class FakeMe:
    id = 1


@pytest.mark.asyncio
async def test_healthy_account_marked_active(db_session, monkeypatch):
    account = _make_account(status="error", status_detail="stale")
    db_session.add(account)
    await db_session.commit()

    async def fake_get_or_connect(*a, **k):
        class Client:
            async def get_me(self):
                return FakeMe()

        return Client()

    monkeypatch.setattr(health_check.pool, "get_or_connect", fake_get_or_connect)

    await health_check.check_account_health(db_session, account)

    assert account.status == "active"
    assert account.status_detail is None
    assert account.last_connected_at is not None


@pytest.mark.asyncio
async def test_banned_account_detected(db_session, monkeypatch):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    async def raise_banned(*a, **k):
        raise UserDeactivatedBanError(request=None)

    monkeypatch.setattr(health_check.pool, "get_or_connect", raise_banned)

    await health_check.check_account_health(db_session, account)

    assert account.status == "banned"


@pytest.mark.asyncio
async def test_revoked_session_marked_error(db_session, monkeypatch):
    account = _make_account()
    db_session.add(account)
    await db_session.commit()

    async def raise_revoked(*a, **k):
        raise AuthKeyUnregisteredError(request=None)

    monkeypatch.setattr(health_check.pool, "get_or_connect", raise_revoked)

    await health_check.check_account_health(db_session, account)

    assert account.status == "error"
    assert "다시 로그인" in account.status_detail


@pytest.mark.asyncio
async def test_pending_login_account_is_skipped(db_session, monkeypatch):
    account = _make_account(status="pending_login")
    db_session.add(account)
    await db_session.commit()

    called = False

    async def fake_get_or_connect(*a, **k):
        nonlocal called
        called = True

    monkeypatch.setattr(health_check.pool, "get_or_connect", fake_get_or_connect)

    await health_check.check_account_health(db_session, account)

    assert called is False
    assert account.status == "pending_login"


@pytest.mark.asyncio
async def test_flood_waiting_account_is_skipped(db_session, monkeypatch):
    account = _make_account(status="flood_wait", flood_wait_until=datetime.utcnow() + timedelta(minutes=5))
    db_session.add(account)
    await db_session.commit()

    called = False

    async def fake_get_or_connect(*a, **k):
        nonlocal called
        called = True

    monkeypatch.setattr(health_check.pool, "get_or_connect", fake_get_or_connect)

    await health_check.check_account_health(db_session, account)

    assert called is False

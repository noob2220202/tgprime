from unittest.mock import MagicMock

import pytest
from telethon.errors import SessionPasswordNeededError

from app.db.models import TelegramAccount
from app.telegram import login_flow


class FakeSentCode:
    phone_code_hash = "fake-phone-code-hash"


class FakeMe:
    id = 999888777
    username = "testuser"
    first_name = "Test"
    last_name = "User"


class FakeClient:
    """Stand-in for telethon.TelegramClient, avoiding any real network calls."""

    def __init__(self, *args, requires_2fa: bool = False, **kwargs):
        self.connected = False
        self.requires_2fa = requires_2fa
        self.sign_in_calls: list[dict] = []
        self.session = MagicMock()
        self.session.save.return_value = "exported-session-string"

    async def connect(self):
        self.connected = True

    def is_connected(self):
        return self.connected

    async def disconnect(self):
        self.connected = False

    async def send_code_request(self, phone_number):
        return FakeSentCode()

    async def sign_in(self, **kwargs):
        self.sign_in_calls.append(kwargs)
        if "password" not in kwargs and self.requires_2fa:
            raise SessionPasswordNeededError(request=None)

    async def get_me(self):
        return FakeMe()


@pytest.mark.asyncio
async def test_login_without_2fa_creates_account(db_session, monkeypatch):
    monkeypatch.setattr(login_flow, "TelegramClient", lambda *a, **k: FakeClient(*a, requires_2fa=False, **k))

    login_session = await login_flow.start_login(db_session, "My Account", "+15551234567", 12345, "abcdef")
    assert login_session.state == "awaiting_code"

    result_status, account = await login_flow.verify_code(db_session, login_session.id, "12345")

    assert result_status == "done"
    assert account is not None
    assert account.telegram_user_id == FakeMe.id
    assert account.username == "testuser"
    assert account.status == "active"

    # login session is consumed, never left lying around with any secret
    assert await db_session.get(type(login_session), login_session.id) is None


@pytest.mark.asyncio
async def test_login_with_2fa_requires_password_step(db_session, monkeypatch):
    monkeypatch.setattr(login_flow, "TelegramClient", lambda *a, **k: FakeClient(*a, requires_2fa=True, **k))

    login_session = await login_flow.start_login(db_session, "My Account", "+15551234567", 12345, "abcdef")

    result_status, account = await login_flow.verify_code(db_session, login_session.id, "12345")
    assert result_status == "needs_2fa"
    assert account is None

    refreshed = await db_session.get(type(login_session), login_session.id)
    assert refreshed.state == "awaiting_2fa"

    account = await login_flow.verify_2fa(db_session, login_session.id, "hunter2")
    assert account.status == "active"
    assert account.telegram_user_id == FakeMe.id


@pytest.mark.asyncio
async def test_verify_code_with_unknown_session_raises(db_session):
    with pytest.raises(login_flow.LoginSessionExpired):
        await login_flow.verify_code(db_session, "does-not-exist", "12345")


@pytest.mark.asyncio
async def test_finalize_registers_client_in_pool(db_session, monkeypatch):
    from app.telegram.client_pool import pool

    monkeypatch.setattr(login_flow, "TelegramClient", lambda *a, **k: FakeClient(*a, requires_2fa=False, **k))

    login_session = await login_flow.start_login(db_session, "My Account", "+15551234567", 12345, "abcdef")
    _, account = await login_flow.verify_code(db_session, login_session.id, "12345")

    assert account.id in pool._clients
    assert pool._clients[account.id].is_connected()


@pytest.mark.asyncio
async def test_session_and_api_hash_are_encrypted_at_rest(db_session, monkeypatch):
    monkeypatch.setattr(login_flow, "TelegramClient", lambda *a, **k: FakeClient(*a, requires_2fa=False, **k))

    login_session = await login_flow.start_login(db_session, "My Account", "+15551234567", 12345, "abcdef")
    _, account = await login_flow.verify_code(db_session, login_session.id, "12345")

    stored: TelegramAccount = await db_session.get(TelegramAccount, account.id)
    assert stored.session_encrypted != "exported-session-string"
    assert stored.api_hash_encrypted != "abcdef"

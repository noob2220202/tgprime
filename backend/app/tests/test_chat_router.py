from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.db.base import Base, get_db
from app.db.models import TelegramAccount, User
from app.main import app
from app.telegram import account_client
from app.telegram.client_pool import InvalidSessionError
from app.telegram.crypto import encrypt

AUTH_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


class FakeDialog:
    def __init__(self, peer_id, title):
        self.id = peer_id
        self.name = title
        self.is_user = True
        self.is_channel = False
        self.unread_count = 2
        self.message = None
        self.date = datetime.now(timezone.utc)


class FakeMessage:
    def __init__(self, id, text, out=False):
        self.id = id
        self.message = text
        self.out = out
        self.sender_id = 111
        self.date = datetime.now(timezone.utc)


class FakeChatClient:
    def __init__(self):
        self.sent = []

    async def iter_dialogs(self, limit=50):
        for d in [FakeDialog(42, "Alice")]:
            yield d

    async def iter_messages(self, peer, limit=50, offset_id=0):
        for m in [FakeMessage(2, "hi there"), FakeMessage(1, "hello")]:
            yield m

    async def send_message(self, peer, text):
        msg = FakeMessage(99, text, out=True)
        self.sent.append(msg)
        return msg


@pytest_asyncio.fixture
async def client_with_account(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        session.add(User(username="admin", password_hash=hash_password("secret123")))
        account = TelegramAccount(
            label="Test",
            phone_number="+15551234567",
            api_id=1,
            api_hash_encrypted=encrypt("hash"),
            session_encrypted=encrypt("session-string"),
            status="active",
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
        account_id = account.id

    fake_client = FakeChatClient()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_connected_client(db, acc_id):
        yield fake_client

    monkeypatch.setattr(account_client, "connected_client", fake_connected_client)
    monkeypatch.setattr("app.routers.chat.connected_client", fake_connected_client)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login", json={"username": "admin", "password": "secret123"}, headers=AUTH_HEADERS
        )
        assert res.status_code == 200
        yield ac, account_id, fake_client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_dialogs(client_with_account):
    ac, account_id, _ = client_with_account
    res = await ac.get(f"/api/accounts/{account_id}/dialogs")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["title"] == "Alice"
    assert body[0]["peer_id"] == 42


@pytest.mark.asyncio
async def test_get_messages_returns_oldest_first(client_with_account):
    ac, account_id, _ = client_with_account
    res = await ac.get(f"/api/accounts/{account_id}/dialogs/42/messages")
    assert res.status_code == 200
    body = res.json()
    assert [m["id"] for m in body] == [1, 2]


@pytest.mark.asyncio
async def test_send_message(client_with_account):
    ac, account_id, fake_client = client_with_account
    res = await ac.post(
        f"/api/accounts/{account_id}/dialogs/42/messages", json={"text": "hello world"}, headers=AUTH_HEADERS
    )
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "hello world"
    assert body["out"] is True
    assert len(fake_client.sent) == 1


@pytest.mark.asyncio
async def test_corrupt_session_returns_400_not_500(monkeypatch):
    # Exercises the *real* connected_client / pool.get_or_connect path (not
    # mocked away like the fixture above) to make sure a corrupted session
    # string surfaces as a clean 400 instead of crashing with a 500.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_maker() as session:
        session.add(User(username="admin", password_hash=hash_password("secret123")))
        account = TelegramAccount(
            label="Test",
            api_id=1,
            api_hash_encrypted=encrypt("hash"),
            session_encrypted=encrypt("not-a-real-session-string"),
            status="active",
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
        account_id = account.id

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/auth/login", json={"username": "admin", "password": "secret123"}, headers=AUTH_HEADERS
            )
            assert res.status_code == 200

            res = await ac.get(f"/api/accounts/{account_id}/dialogs")
            assert res.status_code == 400
            assert "세션" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.db.base import Base, get_db
from app.db.models import TelegramAccount, User
from app.main import app
from app.telegram.crypto import encrypt

AUTH_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


class FakeStoryClient:
    def __init__(self):
        self.posted = []


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
            label="Test", api_id=1, api_hash_encrypted=encrypt("h"), session_encrypted=encrypt("s"), status="active"
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
        account_id = account.id

    fake_client = FakeStoryClient()

    @asynccontextmanager
    async def fake_connected_client(db, acc_id):
        yield fake_client

    async def fake_post_photo_story(client, photo_bytes, caption=None):
        client.posted.append((photo_bytes, caption))

    monkeypatch.setattr("app.routers.stories.connected_client", fake_connected_client)
    monkeypatch.setattr("app.routers.stories.post_photo_story", fake_post_photo_story)

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
async def test_post_story_succeeds(client_with_account):
    ac, account_id, fake_client = client_with_account
    res = await ac.post(
        f"/api/accounts/{account_id}/story",
        data={"caption": "my story"},
        files={"photo": ("story.jpg", b"fake-bytes", "image/jpeg")},
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert len(fake_client.posted) == 1
    assert fake_client.posted[0][1] == "my story"


@pytest.mark.asyncio
async def test_post_story_requires_auth():
    from app.main import app as raw_app

    transport = ASGITransport(app=raw_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/accounts/some-id/story",
            files={"photo": ("s.jpg", b"x", "image/jpeg")},
            headers=AUTH_HEADERS,
        )
    assert res.status_code == 401

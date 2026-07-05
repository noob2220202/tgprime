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


@pytest_asyncio.fixture
async def client_with_account():
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login", json={"username": "admin", "password": "secret123"}, headers=AUTH_HEADERS
        )
        assert res.status_code == 200
        yield ac, account_id

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_auto_reply_defaults_to_disabled(client_with_account):
    ac, account_id = client_with_account
    res = await ac.get(f"/api/accounts/{account_id}/auto-reply")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["reply_text"] == ""


@pytest.mark.asyncio
async def test_update_auto_reply(client_with_account):
    ac, account_id = client_with_account
    res = await ac.put(
        f"/api/accounts/{account_id}/auto-reply",
        json={"enabled": True, "reply_text": "지금은 답장이 어렵습니다.", "cooldown_minutes": 30},
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is True
    assert body["cooldown_minutes"] == 30

    get_res = await ac.get(f"/api/accounts/{account_id}/auto-reply")
    assert get_res.json()["reply_text"] == "지금은 답장이 어렵습니다."


@pytest.mark.asyncio
async def test_auto_reply_requires_auth():
    from app.main import app as raw_app

    transport = ASGITransport(app=raw_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/accounts/some-id/auto-reply")
    assert res.status_code == 401

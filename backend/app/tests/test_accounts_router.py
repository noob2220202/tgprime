import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.db.base import Base, get_db
from app.db.models import User
from app.main import app
from app.telegram import login_flow
from app.tests.test_login_flow import FakeClient


@pytest_asyncio.fixture
async def client(monkeypatch):
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
        await session.commit()

    monkeypatch.setattr(login_flow, "TelegramClient", lambda *a, **k: FakeClient(*a, requires_2fa=False, **k))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


AUTH_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


async def _login(ac: AsyncClient) -> None:
    res = await ac.post(
        "/api/auth/login", json={"username": "admin", "password": "secret123"}, headers=AUTH_HEADERS
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_accounts_endpoints_require_auth(client: AsyncClient):
    res = await client.get("/api/accounts")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_full_login_flow_creates_listable_account(client: AsyncClient):
    await _login(client)

    start_res = await client.post(
        "/api/accounts/login/start",
        json={"label": "Test", "phone_number": "+15551234567", "api_id": 123, "api_hash": "abc"},
        headers=AUTH_HEADERS,
    )
    assert start_res.status_code == 200
    login_session_id = start_res.json()["login_session_id"]

    verify_res = await client.post(
        "/api/accounts/login/verify-code",
        json={"login_session_id": login_session_id, "code": "12345"},
        headers=AUTH_HEADERS,
    )
    assert verify_res.status_code == 200
    body = verify_res.json()
    assert body["status"] == "done"
    assert body["account"]["username"] == "testuser"

    list_res = await client.get("/api/accounts")
    assert list_res.status_code == 200
    accounts = list_res.json()
    assert len(accounts) == 1
    assert accounts[0]["status"] == "active"


@pytest.mark.asyncio
async def test_mutating_request_without_csrf_header_is_rejected(client: AsyncClient):
    res = await client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert res.status_code == 403

import json

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
async def client_with_accounts():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    account_ids = []
    async with session_maker() as session:
        session.add(User(username="admin", password_hash=hash_password("secret123")))
        for label in ["A", "B"]:
            account = TelegramAccount(
                label=label,
                api_id=1,
                api_hash_encrypted=encrypt("hash"),
                session_encrypted=encrypt("session"),
                status="active",
            )
            session.add(account)
            await session.flush()
            account_ids.append(account.id)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login", json={"username": "admin", "password": "secret123"}, headers=AUTH_HEADERS
        )
        assert res.status_code == 200
        yield ac, account_ids

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_bulk_job_creates_item_per_account(client_with_accounts):
    ac, account_ids = client_with_accounts

    payload = {"account_ids": account_ids, "first_name": "Bulk", "bio": "Updated bio"}
    res = await ac.post(
        "/api/bulk-jobs",
        data={"payload": json.dumps(payload)},
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 200
    job = res.json()
    assert job["total_items"] == 2
    assert job["status"] in ("pending", "running")

    detail_res = await ac.get(f"/api/bulk-jobs/{job['id']}", headers=AUTH_HEADERS)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["items"]) == 2
    assert {item["account_id"] for item in detail["items"]} == set(account_ids)


@pytest.mark.asyncio
async def test_create_bulk_job_without_fields_rejected(client_with_accounts):
    ac, account_ids = client_with_accounts

    payload = {"account_ids": account_ids}
    res = await ac.post(
        "/api/bulk-jobs",
        data={"payload": json.dumps(payload)},
        headers=AUTH_HEADERS,
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_list_jobs_requires_auth():
    from app.main import app as raw_app

    transport = ASGITransport(app=raw_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/bulk-jobs")
    assert res.status_code == 401

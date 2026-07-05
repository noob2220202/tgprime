import os

os.environ.setdefault("MASTER_ENCRYPTION_KEY", "_Kv6NKlRRAEDFu2TqzNXqhKGq-of9aL1jq6jveCFpok=")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_client_pool():
    from app.telegram.client_pool import pool

    pool._clients.clear()
    pool._last_used.clear()
    yield
    pool._clients.clear()
    pool._last_used.clear()

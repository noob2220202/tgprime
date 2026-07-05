from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient

from app.db.models import TelegramAccount
from app.telegram.client_pool import pool
from app.telegram.crypto import decrypt


@asynccontextmanager
async def connected_client(db: AsyncSession, account_id: str):
    """Yields a live, connected TelegramClient for account_id, holding the
    account's pool lock for the duration so no other request races it."""
    account = await db.get(TelegramAccount, account_id)
    if account is None:
        raise LookupError("account not found")

    async with pool.lock(account_id):
        client: TelegramClient = await pool.get_or_connect(
            account_id,
            account.api_id,
            decrypt(account.api_hash_encrypted),
            decrypt(account.session_encrypted),
        )
        yield client

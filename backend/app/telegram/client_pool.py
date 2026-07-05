import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from telethon import TelegramClient
from telethon.sessions import StringSession


class ClientPool:
    """Holds at most one live TelegramClient per account_id within this process.

    A per-account asyncio.Lock guarantees that a bulk job and a live web-client
    session never issue overlapping requests on the same MTProto connection.
    """

    def __init__(self) -> None:
        self._clients: dict[str, TelegramClient] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_used: dict[str, datetime] = {}

    def lock(self, account_id: str) -> asyncio.Lock:
        return self._locks[account_id]

    async def get_or_connect(self, account_id: str, api_id: int, api_hash: str, session_str: str) -> TelegramClient:
        self._last_used[account_id] = datetime.utcnow()
        client = self._clients.get(account_id)
        if client is not None and client.is_connected():
            return client

        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        self._clients[account_id] = client
        return client

    def register(self, account_id: str, client: TelegramClient) -> None:
        """Hand off an already-connected client (e.g. one that just finished login)."""
        self._clients[account_id] = client
        self._last_used[account_id] = datetime.utcnow()

    async def disconnect(self, account_id: str) -> None:
        client = self._clients.pop(account_id, None)
        self._last_used.pop(account_id, None)
        if client is not None:
            await client.disconnect()

    async def disconnect_idle(self, max_idle: timedelta) -> None:
        cutoff = datetime.utcnow() - max_idle
        stale_ids = [aid for aid, ts in self._last_used.items() if ts < cutoff]
        for account_id in stale_ids:
            await self.disconnect(account_id)

    async def disconnect_all(self) -> None:
        for account_id in list(self._clients.keys()):
            await self.disconnect(account_id)


pool = ClientPool()

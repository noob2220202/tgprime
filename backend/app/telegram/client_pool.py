import asyncio
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta

from telethon import TelegramClient
from telethon.sessions import StringSession


class InvalidSessionError(RuntimeError):
    """Raised when a stored session can't be parsed or connected — a
    corrupted/foreign session string, not a transient network issue."""


class ClientPool:
    """Holds at most one live TelegramClient per account_id within this process.

    A per-account asyncio.Lock guarantees that a bulk job and a live web-client
    session never issue overlapping requests on the same MTProto connection.
    """

    def __init__(self) -> None:
        self._clients: dict[str, TelegramClient] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_used: dict[str, datetime] = {}
        self._new_client_hooks: list[Callable[[str, TelegramClient], None]] = []

    def lock(self, account_id: str) -> asyncio.Lock:
        return self._locks[account_id]

    def on_new_client(self, hook: Callable[[str, TelegramClient], None]) -> None:
        """Registers a callback invoked whenever a *new* client is added to the
        pool (fresh connect or hand-off from login/import) — e.g. to attach
        feature-specific event handlers like auto-reply without coupling
        this generic pool to those features."""
        self._new_client_hooks.append(hook)

    def _run_new_client_hooks(self, account_id: str, client: TelegramClient) -> None:
        for hook in self._new_client_hooks:
            hook(account_id, client)

    async def get_or_connect(self, account_id: str, api_id: int, api_hash: str, session_str: str) -> TelegramClient:
        self._last_used[account_id] = datetime.utcnow()
        client = self._clients.get(account_id)
        if client is not None and client.is_connected():
            return client

        try:
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()
        except Exception as e:
            raise InvalidSessionError(f"세션에 연결할 수 없습니다: {e}") from e

        self._clients[account_id] = client
        self._run_new_client_hooks(account_id, client)
        return client

    def register(self, account_id: str, client: TelegramClient) -> None:
        """Hand off an already-connected client (e.g. one that just finished login)."""
        self._clients[account_id] = client
        self._last_used[account_id] = datetime.utcnow()
        self._run_new_client_hooks(account_id, client)

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

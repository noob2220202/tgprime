import pytest

from app.telegram.client_pool import ClientPool, InvalidSessionError


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.connected = False

    async def connect(self):
        self.connected = True

    def is_connected(self):
        return self.connected

    async def disconnect(self):
        self.connected = False


@pytest.mark.asyncio
async def test_get_or_connect_reuses_existing_connected_client(monkeypatch):
    pool = ClientPool()
    monkeypatch.setattr("app.telegram.client_pool.TelegramClient", FakeClient)
    monkeypatch.setattr("app.telegram.client_pool.StringSession", lambda s: s)

    client1 = await pool.get_or_connect("acc-1", 1, "hash", "session")
    client2 = await pool.get_or_connect("acc-1", 1, "hash", "session")

    assert client1 is client2


@pytest.mark.asyncio
async def test_disconnect_removes_client(monkeypatch):
    pool = ClientPool()
    monkeypatch.setattr("app.telegram.client_pool.TelegramClient", FakeClient)
    monkeypatch.setattr("app.telegram.client_pool.StringSession", lambda s: s)

    client = await pool.get_or_connect("acc-1", 1, "hash", "session")
    await pool.disconnect("acc-1")

    assert "acc-1" not in pool._clients
    assert client.connected is False


@pytest.mark.asyncio
async def test_locks_are_per_account():
    pool = ClientPool()
    assert pool.lock("acc-1") is pool.lock("acc-1")
    assert pool.lock("acc-1") is not pool.lock("acc-2")


@pytest.mark.asyncio
async def test_disconnect_all(monkeypatch):
    pool = ClientPool()
    monkeypatch.setattr("app.telegram.client_pool.TelegramClient", FakeClient)
    monkeypatch.setattr("app.telegram.client_pool.StringSession", lambda s: s)

    await pool.get_or_connect("acc-1", 1, "hash", "session")
    await pool.get_or_connect("acc-2", 1, "hash", "session")

    await pool.disconnect_all()

    assert pool._clients == {}


@pytest.mark.asyncio
async def test_new_client_hook_fires_on_get_or_connect(monkeypatch):
    pool = ClientPool()
    monkeypatch.setattr("app.telegram.client_pool.TelegramClient", FakeClient)
    monkeypatch.setattr("app.telegram.client_pool.StringSession", lambda s: s)

    calls = []
    pool.on_new_client(lambda account_id, client: calls.append((account_id, client)))

    client = await pool.get_or_connect("acc-1", 1, "hash", "session")
    assert calls == [("acc-1", client)]

    # Reusing the cached connection must not re-fire the hook.
    await pool.get_or_connect("acc-1", 1, "hash", "session")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_new_client_hook_fires_on_register():
    pool = ClientPool()
    calls = []
    pool.on_new_client(lambda account_id, client: calls.append((account_id, client)))

    client = FakeClient()
    pool.register("acc-1", client)

    assert calls == [("acc-1", client)]


@pytest.mark.asyncio
async def test_corrupt_session_raises_invalid_session_error():
    # Uses the real StringSession (not mocked) — a garbage string must be
    # surfaced as a clean, catchable error instead of crashing the caller.
    pool = ClientPool()

    with pytest.raises(InvalidSessionError):
        await pool.get_or_connect("acc-1", 12345, "hash", "not-a-real-session-string")

    assert "acc-1" not in pool._clients

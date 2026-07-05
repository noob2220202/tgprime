import pytest

from app.db.models import TelegramAccount
from app.telegram import session_import
from app.telegram.session_import import SessionNotAuthorized


class FakeAuthKey:
    key = b"x" * 256


class FakeSQLiteSession:
    def __init__(self, path):
        self.path = path

    dc_id = 2
    server_address = "149.154.167.51"
    port = 443
    auth_key = FakeAuthKey()


class FakeMe:
    id = 555444333
    username = "importeduser"
    first_name = "Imported"
    last_name = "User"
    phone = "+15559998888"


class FakeImportClient:
    def __init__(self, session, api_id, api_hash, authorized: bool = True):
        self.session = session
        self.authorized = authorized
        self.connected = False

    async def connect(self):
        self.connected = True

    def is_connected(self):
        return self.connected

    async def disconnect(self):
        self.connected = False

    async def is_user_authorized(self):
        return self.authorized

    async def get_me(self):
        return FakeMe()


@pytest.mark.asyncio
async def test_import_authorized_session_creates_account(db_session, monkeypatch):
    monkeypatch.setattr(session_import, "SQLiteSession", FakeSQLiteSession)
    monkeypatch.setattr(
        session_import, "TelegramClient", lambda session, api_id, api_hash: FakeImportClient(session, api_id, api_hash)
    )

    account = await session_import.import_session_file(db_session, "Imported", 12345, "abchash", b"fake-sqlite-bytes")

    assert account.telegram_user_id == FakeMe.id
    assert account.username == "importeduser"
    assert account.phone_number == "+15559998888"
    assert account.status == "active"

    stored: TelegramAccount = await db_session.get(TelegramAccount, account.id)
    assert stored.session_encrypted
    assert stored.api_hash_encrypted != "abchash"


@pytest.mark.asyncio
async def test_import_unauthorized_session_raises(db_session, monkeypatch):
    monkeypatch.setattr(session_import, "SQLiteSession", FakeSQLiteSession)
    monkeypatch.setattr(
        session_import,
        "TelegramClient",
        lambda session, api_id, api_hash: FakeImportClient(session, api_id, api_hash, authorized=False),
    )

    with pytest.raises(SessionNotAuthorized):
        await session_import.import_session_file(db_session, "Imported", 12345, "abchash", b"fake-sqlite-bytes")


@pytest.mark.asyncio
async def test_import_malformed_file_raises_clean_error(db_session):
    # No monkeypatching here: exercises the real SQLiteSession/TelegramClient
    # construction path with garbage bytes that aren't a valid SQLite file at all.
    with pytest.raises(SessionNotAuthorized):
        await session_import.import_session_file(db_session, "Bad", 12345, "abchash", b"this is not sqlite")


@pytest.mark.asyncio
async def test_import_registers_client_in_pool(db_session, monkeypatch):
    from app.telegram.client_pool import pool

    monkeypatch.setattr(session_import, "SQLiteSession", FakeSQLiteSession)
    monkeypatch.setattr(
        session_import, "TelegramClient", lambda session, api_id, api_hash: FakeImportClient(session, api_id, api_hash)
    )

    account = await session_import.import_session_file(db_session, "Imported", 12345, "abchash", b"fake-sqlite-bytes")

    assert account.id in pool._clients

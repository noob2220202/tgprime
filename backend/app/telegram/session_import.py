import os
import tempfile
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.sessions import SQLiteSession, StringSession

from app.db.models import TelegramAccount
from app.telegram.client_pool import pool
from app.telegram.crypto import encrypt


class SessionNotAuthorized(ValueError):
    pass


async def import_session_file(
    db: AsyncSession, label: str, api_id: int, api_hash: str, file_bytes: bytes
) -> TelegramAccount:
    """Loads an uploaded Telethon `.session` (SQLite) file, verifies it's
    authorized, converts it to a StringSession, and discards the uploaded
    file immediately — mirroring the interactive login's finalize step so
    both onboarding paths end up in the same storage shape.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".session")
    os.close(fd)
    try:
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)

        client = None
        try:
            client = TelegramClient(SQLiteSession(tmp_path), api_id, api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                raise SessionNotAuthorized(
                    "업로드한 세션 파일이 인증되어 있지 않거나 api_id/api_hash가 일치하지 않습니다."
                )

            me = await client.get_me()
            # StringSession.save() only reads attributes common to every
            # Telethon Session implementation, so this converts formats
            # without needing a second connection.
            session_str = StringSession.save(client.session)
        except SessionNotAuthorized:
            if client is not None:
                await client.disconnect()
            raise
        except Exception as e:
            if client is not None:
                await client.disconnect()
            raise SessionNotAuthorized("유효하지 않은 세션 파일입니다.") from e

        account = TelegramAccount(
            label=label,
            api_id=api_id,
            api_hash_encrypted=encrypt(api_hash),
            session_encrypted=encrypt(session_str),
            telegram_user_id=me.id,
            username=me.username,
            first_name=me.first_name,
            last_name=me.last_name,
            phone_number=me.phone,
            status="active",
            last_connected_at=datetime.utcnow(),
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)

        pool.register(account.id, client)
        return account
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

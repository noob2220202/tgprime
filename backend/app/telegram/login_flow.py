from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from app.db.models import LoginSession, TelegramAccount
from app.telegram.client_pool import pool
from app.telegram.crypto import encrypt

LOGIN_SESSION_TTL_MINUTES = 10

# Keyed by LoginSession.id. Holds the live, not-yet-authorized client across the
# multi-step login handshake (send-code -> verify-code -> verify-2fa). Telethon
# requires reusing the same connection for sign_in() to succeed.
_pending_clients: dict[str, TelegramClient] = {}


class LoginSessionExpired(ValueError):
    pass


async def start_login(
    db: AsyncSession, label: str, phone_number: str, api_id: int, api_hash: str
) -> LoginSession:
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    sent = await client.send_code_request(phone_number)

    login_session = LoginSession(
        label=label,
        phone_number=phone_number,
        api_id=api_id,
        api_hash=api_hash,
        telethon_phone_code_hash=sent.phone_code_hash,
        state="awaiting_code",
        expires_at=datetime.utcnow() + timedelta(minutes=LOGIN_SESSION_TTL_MINUTES),
    )
    db.add(login_session)
    await db.commit()
    await db.refresh(login_session)

    _pending_clients[login_session.id] = client
    return login_session


async def _get_pending(db: AsyncSession, login_session_id: str) -> tuple[LoginSession, TelegramClient]:
    login_session = await db.get(LoginSession, login_session_id)
    client = _pending_clients.get(login_session_id)

    if login_session is None or client is None or login_session.expires_at < datetime.utcnow():
        _pending_clients.pop(login_session_id, None)
        if login_session is not None:
            await db.delete(login_session)
            await db.commit()
        raise LoginSessionExpired("로그인 세션이 만료됐습니다. 처음부터 다시 시도해주세요.")

    return login_session, client


async def verify_code(db: AsyncSession, login_session_id: str, code: str) -> tuple[str, TelegramAccount | None]:
    """Returns ("needs_2fa", None) or ("done", account)."""
    login_session, client = await _get_pending(db, login_session_id)

    try:
        await client.sign_in(
            phone=login_session.phone_number,
            code=code,
            phone_code_hash=login_session.telethon_phone_code_hash,
        )
    except SessionPasswordNeededError:
        login_session.state = "awaiting_2fa"
        await db.commit()
        return "needs_2fa", None

    account = await _finalize(db, login_session, client)
    return "done", account


async def verify_2fa(db: AsyncSession, login_session_id: str, password: str) -> TelegramAccount:
    login_session, client = await _get_pending(db, login_session_id)
    await client.sign_in(password=password)
    return await _finalize(db, login_session, client)


async def _finalize(db: AsyncSession, login_session: LoginSession, client: TelegramClient) -> TelegramAccount:
    me = await client.get_me()
    session_str = client.session.save()

    account = TelegramAccount(
        label=login_session.label,
        phone_number=login_session.phone_number,
        api_id=login_session.api_id,
        api_hash_encrypted=encrypt(login_session.api_hash),
        session_encrypted=encrypt(session_str),
        telegram_user_id=me.id,
        username=me.username,
        first_name=me.first_name,
        last_name=me.last_name,
        status="active",
        last_connected_at=datetime.utcnow(),
    )
    db.add(account)
    await db.delete(login_session)
    await db.commit()
    await db.refresh(account)

    _pending_clients.pop(login_session.id, None)
    pool.register(account.id, client)
    return account

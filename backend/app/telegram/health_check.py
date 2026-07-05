from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import (
    AuthKeyUnregisteredError,
    RPCError,
    SessionRevokedError,
    UserDeactivatedBanError,
    UserDeactivatedError,
)

from app.db.models import TelegramAccount
from app.telegram.client_pool import pool
from app.telegram.crypto import decrypt

# Statuses that represent a mid-flow or already-terminal state a background
# health check shouldn't touch.
_SKIP_STATUSES = {"pending_login", "needs_2fa"}


async def check_account_health(db: AsyncSession, account: TelegramAccount) -> None:
    if account.status in _SKIP_STATUSES:
        return
    if account.flood_wait_until and account.flood_wait_until > datetime.utcnow():
        return

    try:
        async with pool.lock(account.id):
            client = await pool.get_or_connect(
                account.id,
                account.api_id,
                decrypt(account.api_hash_encrypted),
                decrypt(account.session_encrypted),
            )
            me = await client.get_me()
        if me is None:
            account.status = "error"
            account.status_detail = "인증되지 않은 세션입니다. 다시 로그인하세요."
        else:
            account.status = "active"
            account.status_detail = None
            account.last_connected_at = datetime.utcnow()
    except (UserDeactivatedBanError, UserDeactivatedError):
        account.status = "banned"
        account.status_detail = "텔레그램에서 계정이 비활성화/차단되었습니다."
    except (AuthKeyUnregisteredError, SessionRevokedError):
        account.status = "error"
        account.status_detail = "세션이 만료되었습니다. 다시 로그인하세요."
    except RPCError as e:
        account.status = "error"
        account.status_detail = str(e)
    except Exception as e:  # connection-level failures (DNS, timeout, etc.)
        account.status = "disconnected"
        account.status_detail = str(e)


async def check_all_accounts(db: AsyncSession) -> None:
    result = await db.execute(select(TelegramAccount))
    for account in result.scalars().all():
        await check_account_health(db, account)
    await db.commit()

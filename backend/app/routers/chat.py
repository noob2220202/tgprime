from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.schemas.chat import DialogOut, MessageOut
from app.telegram.account_client import connected_client

router = APIRouter(prefix="/api/accounts", tags=["chat"], dependencies=[Depends(get_current_user)])


def _peer_type(dialog) -> str:
    if dialog.is_user:
        return "user"
    if dialog.is_channel:
        return "channel"
    return "chat"


@router.get("/{account_id}/dialogs", response_model=list[DialogOut])
async def get_dialogs(account_id: str, db: AsyncSession = Depends(get_db)):
    try:
        async with connected_client(db, account_id) as client:
            dialogs = [d async for d in client.iter_dialogs(limit=50)]
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    return [
        DialogOut(
            peer_id=d.id,
            peer_type=_peer_type(d),
            title=d.name or "",
            unread_count=d.unread_count,
            last_message_text=d.message.message if d.message else None,
            last_message_date=d.date,
        )
        for d in dialogs
    ]


@router.get("/{account_id}/dialogs/{peer_id}/messages", response_model=list[MessageOut])
async def get_messages(
    account_id: str,
    peer_id: int,
    before_id: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    try:
        async with connected_client(db, account_id) as client:
            messages = [m async for m in client.iter_messages(peer_id, limit=limit, offset_id=before_id or 0)]
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Peer not found")

    messages.reverse()  # Telethon returns newest-first; render oldest-first
    return [
        MessageOut(id=m.id, date=m.date, out=m.out, sender_id=m.sender_id, text=m.message or "")
        for m in messages
    ]

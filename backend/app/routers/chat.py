from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import events

from app.auth.dependencies import get_current_user
from app.auth.security import SESSION_COOKIE_NAME, read_session_token
from app.db.base import get_db
from app.db.models import TelegramAccount, User
from app.schemas.chat import DialogOut, MessageOut
from app.telegram.account_client import connected_client
from app.telegram.client_pool import InvalidSessionError, pool
from app.telegram.crypto import decrypt

router = APIRouter(prefix="/api/accounts", tags=["chat"], dependencies=[Depends(get_current_user)])

# Websocket auth is handled manually (see account_live below), so this router
# intentionally has no router-level auth dependency.
ws_router = APIRouter(prefix="/api/accounts", tags=["chat-ws"])


class SendMessageRequest(BaseModel):
    text: str


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
    except InvalidSessionError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

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
    except InvalidSessionError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Peer not found")

    messages.reverse()  # Telethon returns newest-first; render oldest-first
    return [
        MessageOut(id=m.id, date=m.date, out=m.out, sender_id=m.sender_id, text=m.message or "")
        for m in messages
    ]


@router.post("/{account_id}/dialogs/{peer_id}/messages", response_model=MessageOut)
async def send_message(
    account_id: str,
    peer_id: int,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        async with connected_client(db, account_id) as client:
            sent = await client.send_message(peer_id, payload.text)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    except InvalidSessionError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Peer not found")

    return MessageOut(id=sent.id, date=sent.date, out=sent.out, sender_id=sent.sender_id, text=sent.message or "")


async def _authenticate_ws(websocket: WebSocket, db: AsyncSession) -> User | None:
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    user_id = read_session_token(token) if token else None
    if not user_id:
        return None
    return await db.get(User, user_id)


@ws_router.websocket("/{account_id}/live")
async def account_live(websocket: WebSocket, account_id: str, db: AsyncSession = Depends(get_db)):
    user = await _authenticate_ws(websocket, db)
    if user is None:
        await websocket.close(code=4401)
        return

    account = await db.get(TelegramAccount, account_id)
    if account is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()

    try:
        async with pool.lock(account_id):
            client = await pool.get_or_connect(
                account_id, account.api_id, decrypt(account.api_hash_encrypted), decrypt(account.session_encrypted)
            )
    except InvalidSessionError:
        await websocket.close(code=4400)
        return

    async def handler(event) -> None:
        message = event.message
        await websocket.send_json(
            {
                "type": "new_message",
                "peer_id": event.chat_id,
                "message": {
                    "id": message.id,
                    "date": message.date.isoformat(),
                    "out": message.out,
                    "sender_id": message.sender_id,
                    "text": message.message or "",
                },
            }
        )

    client.add_event_handler(handler, events.NewMessage(incoming=True))
    try:
        while True:
            # We don't expect client->server messages, but must await
            # something here to notice when the browser disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        client.remove_event_handler(handler)

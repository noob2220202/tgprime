from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import RPCError

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.telegram.account_client import connected_client
from app.telegram.stories import post_photo_story

MAX_STORY_PHOTO_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/api/accounts", tags=["stories"], dependencies=[Depends(get_current_user)])


@router.post("/{account_id}/story")
async def create_story(
    account_id: str,
    caption: str | None = Form(None),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    photo_bytes = await photo.read()
    if len(photo_bytes) > MAX_STORY_PHOTO_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "사진 파일이 너무 큽니다.")

    try:
        async with connected_client(db, account_id) as client:
            await post_photo_story(client, photo_bytes, caption)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    except RPCError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    return {"ok": True}

from datetime import datetime

from pydantic import BaseModel


class DialogOut(BaseModel):
    peer_id: int
    peer_type: str
    title: str
    unread_count: int
    last_message_text: str | None = None
    last_message_date: datetime | None = None


class MessageOut(BaseModel):
    id: int
    date: datetime
    out: bool
    sender_id: int | None
    text: str

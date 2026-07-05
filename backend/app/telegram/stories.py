from telethon import TelegramClient
from telethon.tl.functions.stories import SendStoryRequest
from telethon.tl.types import InputMediaUploadedPhoto, InputPeerSelf, InputPrivacyValueAllowAll


async def post_photo_story(client: TelegramClient, photo_bytes: bytes, caption: str | None = None) -> None:
    """Posts a photo story to the account's own profile, visible to everyone
    (matches "web Telegram" parity — no view-boosting/automation involved,
    this only publishes content the user supplied)."""
    uploaded = await client.upload_file(photo_bytes, file_name="story.jpg")
    media = InputMediaUploadedPhoto(file=uploaded)
    await client(
        SendStoryRequest(
            peer=InputPeerSelf(),
            media=media,
            privacy_rules=[InputPrivacyValueAllowAll()],
            caption=caption,
        )
    )

from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest


async def update_profile(
    client: TelegramClient,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    about: str | None = None,
) -> None:
    kwargs = {}
    if first_name is not None:
        kwargs["first_name"] = first_name
    if last_name is not None:
        kwargs["last_name"] = last_name
    if about is not None:
        kwargs["about"] = about
    if kwargs:
        await client(UpdateProfileRequest(**kwargs))


async def update_username(client: TelegramClient, username: str) -> None:
    await client(UpdateUsernameRequest(username))


async def update_profile_photo(client: TelegramClient, photo_bytes: bytes) -> None:
    uploaded = await client.upload_file(photo_bytes, file_name="profile.jpg")
    await client(UploadProfilePhotoRequest(file=uploaded))

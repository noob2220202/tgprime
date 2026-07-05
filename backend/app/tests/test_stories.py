import pytest
from telethon.tl.functions.stories import SendStoryRequest
from telethon.tl.types import InputMediaUploadedPhoto

from app.telegram import stories


class FakeClient:
    def __init__(self):
        self.calls = []

    async def upload_file(self, data, file_name=None):
        return f"uploaded:{file_name}:{len(data)}"

    async def __call__(self, request):
        self.calls.append(request)
        return None


@pytest.mark.asyncio
async def test_post_photo_story_sends_expected_request():
    client = FakeClient()

    await stories.post_photo_story(client, b"fake-image-bytes", caption="hello world")

    assert len(client.calls) == 1
    request = client.calls[0]
    assert isinstance(request, SendStoryRequest)
    assert isinstance(request.media, InputMediaUploadedPhoto)
    assert request.caption == "hello world"


@pytest.mark.asyncio
async def test_post_photo_story_without_caption():
    client = FakeClient()

    await stories.post_photo_story(client, b"bytes")

    assert client.calls[0].caption is None

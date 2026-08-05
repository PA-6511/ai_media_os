from __future__ import annotations

import json

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressMediaResponse,
    WordPressRestClient,
)


def jpeg_fixture() -> bytes:
    return (
        b"\xff\xd8"
        + (b"\x00" * 1200)
        + b"\xff\xd9"
    )


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    def read(self) -> bytes:
        return json.dumps(
            self.payload
        ).encode("utf-8")


class FakeOpener:
    def __init__(self, payloads) -> None:
        self.payloads = list(payloads)
        self.requests = []

    def open(self, http_request, timeout):
        self.requests.append(
            (http_request, timeout)
        )
        return FakeResponse(
            self.payloads.pop(0)
        )


def build_client(
    opener: FakeOpener,
) -> WordPressRestClient:
    return WordPressRestClient(
        base_url="https://example.test",
        username="tester",
        application_password="not-a-real-secret",
        opener=opener,
    )


def test_upload_media_uses_media_endpoint() -> None:
    opener = FakeOpener(
        [
            {
                "id": 321,
                "source_url": (
                    "https://example.test/"
                    "wp-content/uploads/cover.jpg"
                ),
                "mime_type": "image/jpeg",
            }
        ]
    )

    client = build_client(opener)

    result = client.upload_media(
        filename="medalist-15-rakuten-kobo.jpg",
        content_type="image/jpeg",
        content=jpeg_fixture(),
    )

    assert result == WordPressMediaResponse(
        media_id=321,
        source_url=(
            "https://example.test/"
            "wp-content/uploads/cover.jpg"
        ),
        mime_type="image/jpeg",
    )

    http_request, timeout = opener.requests[0]

    assert (
        http_request.full_url
        == "https://example.test/wp-json/wp/v2/media"
    )
    assert http_request.method == "POST"
    assert timeout == 30
    assert http_request.data == jpeg_fixture()

    headers = {
        key.lower(): value
        for key, value
        in http_request.header_items()
    }

    assert headers["content-type"] == "image/jpeg"
    assert (
        headers["content-disposition"]
        == (
            'attachment; filename="'
            'medalist-15-rakuten-kobo.jpg"'
        )
    )
    assert headers["authorization"].startswith(
        "Basic "
    )


def test_upload_media_rejects_non_jpeg() -> None:
    opener = FakeOpener([])

    client = build_client(opener)

    with pytest.raises(
        ValueError,
        match="content_type must be image/jpeg",
    ):
        client.upload_media(
            filename="cover.png",
            content_type="image/png",
            content=b"x" * 2000,
        )

    assert opener.requests == []


def test_upload_media_rejects_header_injection() -> None:
    opener = FakeOpener([])

    client = build_client(opener)

    with pytest.raises(
        ValueError,
        match="forbidden characters",
    ):
        client.upload_media(
            filename="cover.jpg\r\nX-Test: unsafe",
            content_type="image/jpeg",
            content=jpeg_fixture(),
        )

    assert opener.requests == []


def test_update_draft_sets_featured_media() -> None:
    opener = FakeOpener(
        [
            {
                "id": 201,
                "status": "draft",
                "link": "https://example.test/?p=201",
            }
        ]
    )

    client = build_client(opener)

    result = client.update_draft(
        post_id=201,
        payload={
            "content": "<p>Updated</p>",
            "featured_media": 321,
        },
    )

    assert result == WordPressDraftResponse(
        post_id=201,
        status="draft",
        link="https://example.test/?p=201",
    )

    http_request, timeout = opener.requests[0]

    assert (
        http_request.full_url
        == (
            "https://example.test/"
            "wp-json/wp/v2/posts/201"
        )
    )
    assert http_request.method == "POST"
    assert timeout == 30

    body = json.loads(
        http_request.data.decode("utf-8")
    )

    assert body == {
        "content": "<p>Updated</p>",
        "featured_media": 321,
        "status": "draft",
    }


def test_update_draft_rejects_publish_status() -> None:
    opener = FakeOpener([])

    client = build_client(opener)

    with pytest.raises(
        ValueError,
        match="update status must be draft",
    ):
        client.update_draft(
            post_id=201,
            payload={
                "content": "<p>Unsafe</p>",
                "status": "publish",
            },
        )

    assert opener.requests == []


def test_update_draft_rejects_invalid_media_id() -> None:
    opener = FakeOpener([])

    client = build_client(opener)

    with pytest.raises(
        ValueError,
        match="featured_media",
    ):
        client.update_draft(
            post_id=201,
            payload={
                "featured_media": 0,
            },
        )

    assert opener.requests == []



def test_get_draft_uses_context_edit_get_request() -> None:
    opener = FakeOpener(
        [
            {
                "id": 201,
                "status": "draft",
                "link": "https://example.test/?p=201",
            }
        ]
    )

    client = build_client(opener)

    result = client.get_draft(
        post_id=201,
    )

    assert result == WordPressDraftResponse(
        post_id=201,
        status="draft",
        link="https://example.test/?p=201",
    )

    http_request, timeout = opener.requests[0]

    assert http_request.full_url == (
        "https://example.test/"
        "wp-json/wp/v2/posts/201?context=edit"
    )
    assert http_request.method == "GET"
    assert http_request.data is None
    assert timeout == 30

    headers = {
        key.lower(): value
        for key, value
        in http_request.header_items()
    }

    assert headers["authorization"].startswith(
        "Basic "
    )
    assert headers["accept"] == "application/json"


def test_get_draft_returns_edit_context_fields_for_safe_updates() -> None:
    opener = FakeOpener(
        [
            {
                "id": 207,
                "status": "draft",
                "link": "https://example.test/?p=207",
                "title": {"raw": "Existing title"},
                "content": {"raw": '<div class="store-buttons"></div>'},
                "excerpt": {"raw": "Existing excerpt"},
                "featured_media": 208,
            }
        ]
    )

    result = build_client(opener).get_draft(post_id=207)

    assert result == WordPressDraftResponse(
        post_id=207,
        status="draft",
        link="https://example.test/?p=207",
        title="Existing title",
        content='<div class="store-buttons"></div>',
        excerpt="Existing excerpt",
        featured_media=208,
    )


def test_get_draft_rejects_non_draft_live_status() -> None:
    from app.integrations.wordpress_rest_client import (
        WordPressTransportError,
    )

    opener = FakeOpener(
        [
            {
                "id": 201,
                "status": "publish",
                "link": "https://example.test/?p=201",
            }
        ]
    )

    client = build_client(opener)

    with pytest.raises(
        WordPressTransportError,
        match="live post is not draft",
    ):
        client.get_draft(
            post_id=201,
        )

    assert len(opener.requests) == 1
    assert opener.requests[0][0].method == "GET"

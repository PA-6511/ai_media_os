from __future__ import annotations

import json

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressRestClient,
    WordPressTransportError,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requests = []

    def open(self, http_request, timeout):
        self.requests.append((http_request, timeout))
        return FakeResponse(self.payload)


def build_client(opener: FakeOpener) -> WordPressRestClient:
    return WordPressRestClient(
        base_url="https://example.test",
        username="tester",
        application_password="not-a-real-secret",
        opener=opener,
    )


def test_create_draft_uses_posts_endpoint_and_draft_payload() -> None:
    opener = FakeOpener(
        {
            "id": 123,
            "status": "draft",
            "link": "https://example.test/?p=123",
        }
    )
    client = build_client(opener)

    result = client.create_draft(
        {
            "title": "Test title",
            "content": "<p>Test</p>",
            "status": "draft",
        }
    )

    assert result == WordPressDraftResponse(
        post_id=123,
        status="draft",
        link="https://example.test/?p=123",
    )

    http_request, timeout = opener.requests[0]
    assert (
        http_request.full_url
        == "https://example.test/wp-json/wp/v2/posts"
    )
    assert http_request.method == "POST"
    assert timeout == 30

    body = json.loads(http_request.data.decode("utf-8"))
    assert body["status"] == "draft"
    assert body["title"] == "Test title"


def test_non_draft_request_is_rejected_before_transport() -> None:
    opener = FakeOpener({"id": 1, "status": "draft"})
    client = build_client(opener)

    with pytest.raises(ValueError, match="status must be draft"):
        client.create_draft(
            {
                "title": "Test",
                "content": "<p>Test</p>",
                "status": "publish",
            }
        )

    assert opener.requests == []


def test_non_draft_response_is_rejected() -> None:
    client = build_client(
        FakeOpener({"id": 123, "status": "publish"})
    )

    with pytest.raises(
        WordPressTransportError,
        match="did not return draft",
    ):
        client.create_draft(
            {
                "title": "Test",
                "content": "<p>Test</p>",
                "status": "draft",
            }
        )

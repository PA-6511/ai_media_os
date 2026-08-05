from __future__ import annotations

import pytest

from app.services.x_r15_public_cover_source import (
    X15PublicCoverError,
    fetch_x15_public_cover,
)


def jpeg_fixture() -> bytes:
    return (
        b"\xff\xd8"
        b"\xff\xe0\x00\x04\x00\x00"
        b"\xff\xc0\x00\x11"
        b"\x08"
        b"\x03\x20"
        b"\x02\x58"
        b"\x03"
        b"\x01\x11\x00"
        b"\x02\x11\x00"
        b"\x03\x11\x00"
        + (b"\x00" * 1100)
        + b"\xff\xd9"
    )


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        content_type: str,
        content: bytes,
        status: int = 200,
    ) -> None:
        self.url = url
        self.status = status
        self.headers = {
            "Content-Type": content_type,
        }
        self.content = content

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    def read(self, limit: int) -> bytes:
        return self.content[:limit]

    def geturl(self) -> str:
        return self.url


class FakeOpener:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.requests = []

    def open(self, http_request, timeout):
        self.requests.append(
            (http_request, timeout)
        )
        return self.responses.pop(0)


def test_fetches_and_validates_rakuten_cover() -> None:
    page_url = (
        "https://books.rakuten.co.jp/rk/example/"
    )
    image_url = (
        "https://tshop.r10s.jp/example/cover.jpg"
    )

    page = (
        '<html><head>'
        f'<meta property="og:image" content="{image_url}">'
        '</head><body>4310000887411</body></html>'
    ).encode("utf-8")

    opener = FakeOpener(
        [
            FakeResponse(
                url=page_url,
                content_type="text/html;charset=UTF-8",
                content=page,
            ),
            FakeResponse(
                url=image_url,
                content_type="image/jpeg",
                content=jpeg_fixture(),
            ),
        ]
    )

    result = fetch_x15_public_cover(
        page_url=page_url,
        expected_marker="4310000887411",
        opener=opener,
    )

    assert result.image_url == image_url
    assert result.content_type == "image/jpeg"
    assert result.width == 600
    assert result.height == 800
    assert result.image_format == "JPEG"
    assert len(result.sha256) == 64
    assert len(opener.requests) == 2


def test_rejects_unapproved_image_host() -> None:
    page_url = (
        "https://books.rakuten.co.jp/rk/example/"
    )

    page = (
        '<html><head>'
        '<meta property="og:image" '
        'content="https://evil.example/cover.jpg">'
        '</head><body>4310000887411</body></html>'
    ).encode("utf-8")

    opener = FakeOpener(
        [
            FakeResponse(
                url=page_url,
                content_type="text/html",
                content=page,
            )
        ]
    )

    with pytest.raises(
        X15PublicCoverError,
        match="allowed cover-image URL",
    ):
        fetch_x15_public_cover(
            page_url=page_url,
            expected_marker="4310000887411",
            opener=opener,
        )

    assert len(opener.requests) == 1


def test_rejects_non_jpeg_response() -> None:
    page_url = (
        "https://books.rakuten.co.jp/rk/example/"
    )
    image_url = (
        "https://tshop.r10s.jp/example/cover.jpg"
    )

    page = (
        '<meta property="og:image" '
        f'content="{image_url}">'
        '4310000887411'
    ).encode("utf-8")

    opener = FakeOpener(
        [
            FakeResponse(
                url=page_url,
                content_type="text/html",
                content=page,
            ),
            FakeResponse(
                url=image_url,
                content_type="text/html",
                content=b"x" * 2000,
            ),
        ]
    )

    with pytest.raises(
        X15PublicCoverError,
        match="must be JPEG",
    ):
        fetch_x15_public_cover(
            page_url=page_url,
            expected_marker="4310000887411",
            opener=opener,
        )


def test_ignores_meta_without_name_or_property() -> None:
    page_url = (
        "https://books.rakuten.co.jp/rk/example/"
    )
    image_url = (
        "https://tshop.r10s.jp/example/cover.jpg"
    )

    page = (
        '<html><head>'
        '<meta charset="utf-8">'
        '<meta content="ignored">'
        f'<meta property="og:image" content="{image_url}">'
        '</head><body>4310000887411</body></html>'
    ).encode("utf-8")

    opener = FakeOpener(
        [
            FakeResponse(
                url=page_url,
                content_type="text/html;charset=UTF-8",
                content=page,
            ),
            FakeResponse(
                url=image_url,
                content_type="image/jpeg",
                content=jpeg_fixture(),
            ),
        ]
    )

    result = fetch_x15_public_cover(
        page_url=page_url,
        expected_marker="4310000887411",
        opener=opener,
    )

    assert result.image_url == image_url
    assert result.width == 600
    assert result.height == 800
    assert len(opener.requests) == 2

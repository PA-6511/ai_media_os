from __future__ import annotations

import hashlib
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib import request
from urllib.parse import urljoin, urlparse


class X15PublicCoverError(RuntimeError):
    pass


@dataclass(frozen=True)
class X15PublicCover:
    page_url: str
    image_url: str
    content_type: str
    content: bytes
    sha256: str
    width: int
    height: int
    image_format: str


class _ImageMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.candidates: list[tuple[int, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {
            str(key).lower(): value or ""
            for key, value in attrs
        }

        if tag.lower() != "meta":
            return

        key = (
            values.get("property")
            or values.get("name")
            or ""
        ).lower()

        priorities = {
            "og:image:secure_url": 0,
            "og:image": 1,
            "twitter:image": 2,
            "twitter:image:src": 3,
        }

        content = values.get("content", "").strip()

        if key in priorities and content:
            self.candidates.append(
                (priorities[key], content)
            )


def _require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise X15PublicCoverError(message)


def _read_limited(
    response: Any,
    limit: int,
) -> bytes:
    content = response.read(limit + 1)

    _require(
        len(content) <= limit,
        "response exceeds configured size limit",
    )

    return content


def _jpeg_dimensions(content: bytes) -> tuple[int, int]:
    _require(
        content.startswith(b"\xff\xd8"),
        "image is not a JPEG file",
    )

    sof_markers = {
        0xC0, 0xC1, 0xC2, 0xC3,
        0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB,
        0xCD, 0xCE, 0xCF,
    }

    position = 2

    while position + 4 <= len(content):
        if content[position] != 0xFF:
            position += 1
            continue

        while (
            position < len(content)
            and content[position] == 0xFF
        ):
            position += 1

        if position >= len(content):
            break

        marker = content[position]
        position += 1

        if marker in {0xD8, 0xD9, 0x01}:
            continue

        if 0xD0 <= marker <= 0xD7:
            continue

        _require(
            position + 2 <= len(content),
            "JPEG segment is truncated",
        )

        segment_length = int.from_bytes(
            content[position:position + 2],
            "big",
        )

        _require(
            segment_length >= 2,
            "JPEG segment length is invalid",
        )

        if marker in sof_markers:
            _require(
                position + 7 <= len(content),
                "JPEG size segment is truncated",
            )

            height = int.from_bytes(
                content[position + 3:position + 5],
                "big",
            )
            width = int.from_bytes(
                content[position + 5:position + 7],
                "big",
            )

            _require(
                width > 0 and height > 0,
                "JPEG dimensions are invalid",
            )

            return width, height

        position += segment_length

    raise X15PublicCoverError(
        "JPEG dimensions were not found"
    )


def fetch_x15_public_cover(
    *,
    page_url: str,
    expected_marker: str,
    opener: Any | None = None,
    timeout_seconds: int = 30,
    max_page_bytes: int = 5 * 1024 * 1024,
    max_image_bytes: int = 20 * 1024 * 1024,
) -> X15PublicCover:
    parsed_page = urlparse(page_url)

    _require(
        parsed_page.scheme == "https",
        "product page must use HTTPS",
    )
    _require(
        parsed_page.hostname == "books.rakuten.co.jp",
        "product page host is not allowed",
    )
    _require(
        bool(expected_marker.strip()),
        "expected marker is required",
    )

    transport = opener or request.build_opener()

    page_request = request.Request(
        page_url,
        headers={
            "User-Agent": "ai-media-os-cover-check/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    with transport.open(
        page_request,
        timeout=timeout_seconds,
    ) as response:
        page_status = response.status
        page_final_url = response.geturl()
        page_content_type = response.headers.get(
            "Content-Type",
            "",
        )
        page_content = _read_limited(
            response,
            max_page_bytes,
        )

    _require(
        200 <= page_status < 400,
        "product page returned a non-success status",
    )
    _require(
        "text/html" in page_content_type.lower(),
        "product page is not HTML",
    )

    html_text = page_content.decode(
        "utf-8",
        errors="replace",
    )

    _require(
        expected_marker in html_text,
        "product identity marker was not found",
    )

    parser = _ImageMetaParser()
    parser.feed(html_text)

    selected_url: str | None = None

    for _, candidate in sorted(parser.candidates):
        normalized = urljoin(
            page_final_url,
            candidate,
        )
        parsed_image = urlparse(normalized)
        hostname = parsed_image.hostname or ""

        if (
            parsed_image.scheme == "https"
            and (
                hostname == "r10s.jp"
                or hostname.endswith(".r10s.jp")
            )
        ):
            selected_url = normalized
            break

    _require(
        selected_url is not None,
        "allowed cover-image URL was not found",
    )

    image_request = request.Request(
        selected_url,
        headers={
            "User-Agent": "ai-media-os-cover-check/1.0",
            "Accept": "image/jpeg",
            "Referer": page_final_url,
        },
    )

    with transport.open(
        image_request,
        timeout=timeout_seconds,
    ) as response:
        image_status = response.status
        image_final_url = response.geturl()
        image_content_type = response.headers.get(
            "Content-Type",
            "",
        ).split(";", 1)[0].strip().lower()
        image_content = _read_limited(
            response,
            max_image_bytes,
        )

    final_hostname = (
        urlparse(image_final_url).hostname or ""
    )

    _require(
        200 <= image_status < 400,
        "cover image returned a non-success status",
    )
    _require(
        (
            final_hostname == "r10s.jp"
            or final_hostname.endswith(".r10s.jp")
        ),
        "cover image redirected to a forbidden host",
    )
    _require(
        image_content_type == "image/jpeg",
        "cover image must be JPEG",
    )
    _require(
        len(image_content) > 1000,
        "cover image is unexpectedly small",
    )

    width, height = _jpeg_dimensions(image_content)

    return X15PublicCover(
        page_url=page_final_url,
        image_url=image_final_url,
        content_type=image_content_type,
        content=image_content,
        sha256=hashlib.sha256(
            image_content
        ).hexdigest(),
        width=width,
        height=height,
        image_format="JPEG",
    )

from __future__ import annotations

import hashlib

import pytest

from scripts.run_x_r11_wordpress_media_draft_update_once import (
    EXPECTED_MEDIA_FILENAME,
    EXPECTED_MEDIA_SLUG,
    EXPECTED_MEDIA_TITLE,
    MEDIA_URL_PLACEHOLDER,
    MediaDraftUpdateExecutionError,
    build_multipart_body,
    build_updated_content,
    extract_wp_text,
    validate_media_object,
)


def test_extract_wp_raw_text() -> None:
    assert extract_wp_text(
        {
            "raw": "テスト"
        }
    ) == "テスト"


def test_updated_content_replaces_placeholder() -> None:
    source = (
        '<img src="'
        + MEDIA_URL_PLACEHOLDER
        + '">'
    )

    media_url = (
        "https://example.com/"
        + EXPECTED_MEDIA_FILENAME
    )

    result = build_updated_content(
        content_preview=source,
        media_source_url=media_url,
    )

    assert MEDIA_URL_PLACEHOLDER not in result
    assert result.count(media_url) == 1


def test_duplicate_placeholder_fails() -> None:
    source = (
        MEDIA_URL_PLACEHOLDER
        + MEDIA_URL_PLACEHOLDER
    )

    with pytest.raises(
        MediaDraftUpdateExecutionError,
        match="must equal one",
    ):
        build_updated_content(
            content_preview=source,
            media_source_url=(
                "https://example.com/"
                + EXPECTED_MEDIA_FILENAME
            ),
        )


def test_multipart_contains_metadata() -> None:
    body, boundary = build_multipart_body(
        fields={
            "slug": EXPECTED_MEDIA_SLUG,
            "title": EXPECTED_MEDIA_TITLE,
        },
        filename=EXPECTED_MEDIA_FILENAME,
        content_type="image/jpeg",
        file_bytes=b"\xff\xd8\xfftest",
    )

    assert boundary.encode("ascii") in body
    assert EXPECTED_MEDIA_SLUG.encode(
        "utf-8"
    ) in body
    assert EXPECTED_MEDIA_TITLE.encode(
        "utf-8"
    ) in body
    assert EXPECTED_MEDIA_FILENAME.encode(
        "utf-8"
    ) in body


def test_valid_media_object_passes() -> None:
    result = validate_media_object(
        {
            "id": 456,
            "slug": EXPECTED_MEDIA_SLUG,
            "status": "inherit",
            "source_url": (
                "https://example.com/"
                "wp-content/uploads/2026/07/"
                + EXPECTED_MEDIA_FILENAME
            ),
            "title": {
                "raw": EXPECTED_MEDIA_TITLE
            },
            "alt_text": EXPECTED_MEDIA_TITLE,
            "caption": {
                "raw": ""
            },
            "description": {
                "raw": ""
            },
            "mime_type": "image/jpeg",
            "post": 195,
            "media_details": {
                "width": 300,
                "height": 373,
            },
        },
        wp_hostname="example.com",
    )

    assert result["media_id"] == 456
    assert result["width"] == 300
    assert result["height"] == 373


def test_media_wrong_attachment_fails() -> None:
    with pytest.raises(
        MediaDraftUpdateExecutionError,
        match="attachment post mismatch",
    ):
        validate_media_object(
            {
                "id": 456,
                "slug": EXPECTED_MEDIA_SLUG,
                "source_url": (
                    "https://example.com/"
                    + EXPECTED_MEDIA_FILENAME
                ),
                "title": {
                    "raw": EXPECTED_MEDIA_TITLE
                },
                "alt_text": EXPECTED_MEDIA_TITLE,
                "mime_type": "image/jpeg",
                "post": 999,
                "media_details": {
                    "width": 300,
                    "height": 373,
                },
            },
            wp_hostname="example.com",
        )

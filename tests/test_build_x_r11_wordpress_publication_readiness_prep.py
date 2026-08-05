from __future__ import annotations

import hashlib

import pytest

from scripts.build_x_r11_wordpress_publication_readiness_prep import (
    EXPECTED_MEDIA_SOURCE_URL,
    EXPECTED_POST_ID,
    PublicationReadinessError,
    build_publication_request_preview,
    site_base_from_rest_base,
    validate_live_draft,
    validate_publication_request_preview,
    validate_single_media_duplicate,
)


def test_site_base_from_rest_base() -> None:
    result = site_base_from_rest_base(
        "https://example.com/wp-json/wp/v2"
    )

    assert result == "https://example.com"


def test_single_media_duplicate_passes() -> None:
    validate_single_media_duplicate(
        {
            "duplicate_found": True,
            "exact_match_count": 1,
            "matched_media_ids": [196],
        }
    )


def test_multiple_media_duplicates_fail() -> None:
    with pytest.raises(
        PublicationReadinessError,
        match="must equal one",
    ):
        validate_single_media_duplicate(
            {
                "duplicate_found": True,
                "exact_match_count": 2,
                "matched_media_ids": [
                    196,
                    197,
                ],
            }
        )


def test_valid_live_draft_passes() -> None:
    content = (
        '<article class="ebook-new-release-article">'
        '<div class="ebook-pr-disclosure">PR</div>'
        '<figure class="ebook-cover-image">'
        f'<img src="{EXPECTED_MEDIA_SOURCE_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
        '<div class="price-cards"></div>'
        '<div class="store-buttons"></div>'
        "</article>"
    )

    result = validate_live_draft(
        {
            "id": EXPECTED_POST_ID,
            "status": "draft",
            "slug": (
                "noa-senpai-wa-tomodachi-"
                "11-6ffa7a8d"
            ),
            "title": {
                "raw": (
                    "のあ先輩はともだち。 "
                    "第11巻｜配信開始"
                )
            },
            "categories": [43],
            "content": {
                "raw": content
            },
            "link": (
                "https://example.com/?p=195"
            ),
        },
        expected_content_sha256=(
            hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()
        ),
    )

    assert result["post_id"] == 195
    assert result["status"] == "draft"


def test_publish_status_before_execution_fails() -> None:
    content = (
        '<article class="ebook-new-release-article">'
        '<div class="ebook-pr-disclosure">PR</div>'
        '<figure class="ebook-cover-image">'
        f'<img src="{EXPECTED_MEDIA_SOURCE_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
        '<div class="price-cards"></div>'
        '<div class="store-buttons"></div>'
        "</article>"
    )

    with pytest.raises(
        PublicationReadinessError,
        match="must remain draft",
    ):
        validate_live_draft(
            {
                "id": EXPECTED_POST_ID,
                "status": "publish",
                "slug": (
                    "noa-senpai-wa-tomodachi-"
                    "11-6ffa7a8d"
                ),
                "title": {
                    "raw": (
                        "のあ先輩はともだち。 "
                        "第11巻｜配信開始"
                    )
                },
                "categories": [43],
                "content": {
                    "raw": content
                },
                "link": (
                    "https://example.com/"
                ),
            },
            expected_content_sha256=(
                hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()
            ),
        )


def test_publication_preview_passes() -> None:
    preview = (
        build_publication_request_preview()
    )

    validate_publication_request_preview(
        preview
    )

    assert preview[
        "payload"
    ] == {
        "status": "publish",
    }

    assert preview[
        "execution_allowed"
    ] is False

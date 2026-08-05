from __future__ import annotations

from datetime import date

import pytest

from app.services.x_r13_wordpress_draft_payload_adapter import (
    X13WordPressDraftInput,
    X13WordPressDraftPayloadError,
    build_x_r13_wordpress_draft_payload,
)


def build_input(**overrides):
    values = {
        "ebook_item_id": (
            "e2029b2f-f44a-462f-abc8-86c4bc74b818"
        ),
        "title": "メダリスト",
        "volume_label": "第15巻",
        "author_name": "つるまいかだ",
        "publisher_name": "講談社",
        "release_date": date(2026, 7, 22),
        "item_type": "tankobon",
        "store_name": "RAKUTEN_KOBO",
        "store_item_id": "4310000887411",
        "affiliate_url": (
            "https://example.test/affiliate"
        ),
        "cover_image_url": (
            "https://hoshido.jp/"
            "wp-content/uploads/cover.jpg"
        ),
    }

    values.update(overrides)

    return X13WordPressDraftInput(**values)


def test_payload_contains_cover_image() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input()
    )

    content = payload["content"]

    assert "ebook-cover-figure" in content
    assert "ebook-cover-image" in content
    assert (
        'src="https://hoshido.jp/'
        'wp-content/uploads/cover.jpg"'
        in content
    )
    assert 'alt="メダリスト 第15巻 書影"' in content
    assert 'loading="lazy"' in content
    assert "<h1" not in content
    assert "ebook-release-metadata-card" in content
    assert "ebook-store-button-rakuten-kobo" in content


def test_payload_without_cover_still_works() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input(cover_image_url=None)
    )

    content = payload["content"]

    assert "ebook-cover-image" not in content
    assert "ebook-release-metadata-card" in content


def test_payload_rejects_non_https_cover() -> None:
    with pytest.raises(
        X13WordPressDraftPayloadError,
        match="cover_image_url must use HTTPS",
    ):
        build_x_r13_wordpress_draft_payload(
            build_input(
                cover_image_url=(
                    "http://example.test/cover.jpg"
                )
            )
        )

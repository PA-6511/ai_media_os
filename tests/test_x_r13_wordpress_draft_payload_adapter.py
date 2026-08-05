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
        "store_name": "rakuten_kobo",
        "store_item_id": "4310000887411",
        "affiliate_url": "https://example.test/affiliate",
    }
    values.update(overrides)
    return X13WordPressDraftInput(**values)


def test_build_payload_is_draft_only() -> None:
    payload = build_x_r13_wordpress_draft_payload(build_input())

    assert payload["title"] == "メダリスト 第15巻"
    assert payload["status"] == "draft"
    assert payload["slug"] == "medalist-15-rakuten-kobo"
    assert "プロモーションを含みます" in payload["content"]
    assert 'rel="sponsored nofollow"' in payload["content"]
    assert "4310000887411" in payload["content"]


def test_payload_escapes_untrusted_values() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input(author_name="<script>alert(1)</script>")
    )

    assert "<script>" not in payload["content"]
    assert "&lt;script&gt;" in payload["content"]


def test_non_https_affiliate_url_is_rejected() -> None:
    with pytest.raises(
        X13WordPressDraftPayloadError,
        match="must use HTTPS",
    ):
        build_x_r13_wordpress_draft_payload(
            build_input(affiliate_url="http://example.test")
        )


def test_wrong_candidate_is_rejected() -> None:
    with pytest.raises(
        X13WordPressDraftPayloadError,
        match="does not match X-R13",
    ):
        build_x_r13_wordpress_draft_payload(
            build_input(ebook_item_id="another-item")
        )

# X_R13_VISUAL_PAYLOAD_TESTS_START
def test_payload_avoids_duplicate_body_heading() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input()
    )

    assert payload["title"] == "メダリスト 第15巻"
    assert "<h1" not in payload["content"]


def test_payload_uses_metadata_card_and_store_button() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input()
    )

    content = payload["content"]

    assert "ebook-release-metadata-card" in content
    assert "ebook-release-metadata" in content
    assert "ebook-store-button-rakuten-kobo" in content
    assert "楽天Koboで読む・購入する" in content
    assert 'rel="sponsored nofollow"' in content


def test_store_item_id_is_hidden_metadata() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input()
    )

    content = payload["content"]

    assert (
        'data-store-item-id="4310000887411"'
        in content
    )
    assert "楽天Kobo商品ID:" not in content


def test_store_item_id_attribute_is_escaped() -> None:
    payload = build_x_r13_wordpress_draft_payload(
        build_input(
            store_item_id='4310" data-unsafe="1'
        )
    )

    content = payload["content"]

    assert 'data-unsafe="1"' not in content
    assert "&quot;" in content
# X_R13_VISUAL_PAYLOAD_TESTS_END


from __future__ import annotations

import hashlib

import pytest

from scripts.build_x_r11_wordpress_publication_human_review_prep import (
    BLOCKED_OLD_PRODUCT_HASH,
    CURRENT_PRODUCT_HASH,
    EXPECTED_MEDIA_SOURCE_URL,
    PublicationHumanReviewError,
    build_review_checklist,
    validate_pending_checklist,
    validate_review_content,
)


def valid_content() -> str:
    return (
        '<article class="ebook-new-release-article">'
        '<div class="ebook-pr-disclosure">PR</div>'
        '<figure class="ebook-cover-image">'
        f'<img src="{EXPECTED_MEDIA_SOURCE_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
        '<div class="price-cards"></div>'
        '<div class="store-buttons">'
        '<a href="https://hb.afl.rakuten.co.jp/'
        'example/?pc=https%3A%2F%2F'
        'product.rakuten.co.jp%2Fproduct%2F-%2F'
        f'{CURRENT_PRODUCT_HASH}%2F">'
        "楽天Kobo"
        "</a>"
        "</div>"
        "</article>"
    )


def test_twelve_pending_checks_pass() -> None:
    validate_pending_checklist(
        build_review_checklist()
    )


def test_duplicate_check_id_fails() -> None:
    checklist = build_review_checklist()

    checklist[1]["check_id"] = (
        checklist[0]["check_id"]
    )

    with pytest.raises(
        PublicationHumanReviewError,
        match="not unique",
    ):
        validate_pending_checklist(
            checklist
        )


def test_non_pending_check_fails() -> None:
    checklist = build_review_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        PublicationHumanReviewError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_valid_review_content_passes() -> None:
    content = valid_content()

    result = validate_review_content(
        content,
        expected_content_sha256=(
            hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()
        ),
    )

    assert result[
        "affiliate_url_count"
    ] == 1

    assert result[
        "current_affiliate_hash_verified"
    ] is True


def test_old_affiliate_hash_fails() -> None:
    content = valid_content().replace(
        CURRENT_PRODUCT_HASH,
        BLOCKED_OLD_PRODUCT_HASH,
        1,
    )

    with pytest.raises(
        PublicationHumanReviewError,
        match="superseded affiliate hash",
    ):
        validate_review_content(
            content,
            expected_content_sha256=(
                hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()
            ),
        )

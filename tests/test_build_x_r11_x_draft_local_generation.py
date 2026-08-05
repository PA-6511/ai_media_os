from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_local_generation import (
    BLOCKED_OLD_PRODUCT_HASH,
    PUBLIC_URL_PLACEHOLDER,
    XDraftGenerationError,
    build_x_draft_text,
    estimated_x_character_count,
    extract_affiliate_url,
    validate_x_draft_text,
)


def valid_affiliate_html() -> str:
    return (
        '<a href="https://hb.afl.rakuten.co.jp/'
        'example/?pc=https%3A%2F%2F'
        'product.rakuten.co.jp%2Fproduct%2F-%2F'
        'bce9f1878b0032dc4745ecf22fd179a6%2F'
        '&amp;link_type=hybrid_url">'
        '楽天Kobo'
        '</a>'
    )


def test_extract_current_affiliate_url() -> None:
    value = extract_affiliate_url(
        valid_affiliate_html()
    )

    assert (
        "bce9f1878b0032dc4745ecf22fd179a6"
        in value
    )


def test_old_affiliate_hash_is_rejected() -> None:
    value = valid_affiliate_html().replace(
        "bce9f1878b0032dc4745ecf22fd179a6",
        BLOCKED_OLD_PRODUCT_HASH,
    )

    with pytest.raises(
        XDraftGenerationError,
        match="current affiliate product hash",
    ):
        extract_affiliate_url(value)


def test_draft_contains_public_url_placeholder() -> None:
    draft = build_x_draft_text()

    assert draft.count(
        PUBLIC_URL_PLACEHOLDER
    ) == 1


def test_draft_estimate_is_within_limit() -> None:
    draft = build_x_draft_text()

    assert (
        estimated_x_character_count(
            draft
        )
        <= 280
    )


def test_complete_draft_validation_passes() -> None:
    result = validate_x_draft_text(
        build_x_draft_text()
    )

    assert result[
        "character_limit_passed"
    ] is True

    assert result[
        "raw_affiliate_url_in_text"
    ] is False

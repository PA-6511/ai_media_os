from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_public_url_replacement_local_prep import (
    EXPECTED_LITERAL_CHARACTER_COUNT,
    EXPECTED_PUBLIC_URL,
    EXPECTED_REPLACED_TEXT,
    EXPECTED_REPLACED_TEXT_SHA,
    EXPECTED_SOURCE_TEXT,
    EXPECTED_TCO_CHARACTER_COUNT,
    PUBLIC_URL_PLACEHOLDER,
    XDraftPublicUrlReplacementError,
    estimate_tco_character_count,
    replace_public_url,
    sha256_text,
    validate_source_text,
)


def test_fixed_source_text_passes() -> None:
    validate_source_text(
        EXPECTED_SOURCE_TEXT
    )


def test_changed_source_wording_fails() -> None:
    changed = EXPECTED_SOURCE_TEXT.replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XDraftPublicUrlReplacementError,
        match="differs from fixed text",
    ):
        validate_source_text(
            changed
        )


def test_public_url_replacement_passes() -> None:
    result = replace_public_url(
        EXPECTED_SOURCE_TEXT
    )

    assert result == EXPECTED_REPLACED_TEXT

    assert sha256_text(
        result
    ) == EXPECTED_REPLACED_TEXT_SHA

    assert PUBLIC_URL_PLACEHOLDER not in result

    assert result.count(
        EXPECTED_PUBLIC_URL
    ) == 1


def test_duplicate_placeholder_fails() -> None:
    source = (
        EXPECTED_SOURCE_TEXT
        + "\n"
        + PUBLIC_URL_PLACEHOLDER
    )

    with pytest.raises(
        XDraftPublicUrlReplacementError,
        match="differs from fixed text",
    ):
        replace_public_url(
            source
        )


def test_wrong_public_url_fails() -> None:
    with pytest.raises(
        XDraftPublicUrlReplacementError,
        match="public URL mismatch",
    ):
        replace_public_url(
            EXPECTED_SOURCE_TEXT,
            "https://hoshido.jp/wrong/",
        )


def test_character_counts_pass() -> None:
    result = replace_public_url(
        EXPECTED_SOURCE_TEXT
    )

    assert len(result) == (
        EXPECTED_LITERAL_CHARACTER_COUNT
    )

    assert estimate_tco_character_count(
        result
    ) == EXPECTED_TCO_CHARACTER_COUNT

import scripts.build_x_r11_x_draft_public_url_replacement_local_prep as local_prep_module


def test_source_pack_without_public_url_resolution_fields_passes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        local_prep_module,
        "verify_expected_digest",
        lambda *args, **kwargs: (
            "x_draft_local_generation_digest_sha256"
        ),
    )

    local_prep_module.validate_source_x_draft_pack(
        {
            "status": "PASS_X_DRAFT_LOCAL_GENERATION",
            "x_draft": {
                "draft_id": (
                    local_prep_module
                    .EXPECTED_SOURCE_DRAFT_ID
                ),
                "text": (
                    local_prep_module
                    .EXPECTED_SOURCE_TEXT
                ),
                "text_sha256": (
                    local_prep_module
                    .EXPECTED_SOURCE_TEXT_SHA
                ),
            },
            "normal_x_fb_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
        }
    )


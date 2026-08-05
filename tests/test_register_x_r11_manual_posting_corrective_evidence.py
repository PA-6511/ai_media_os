from __future__ import annotations

import hashlib

import pytest

from scripts.register_x_r11_manual_posting_corrective_evidence import (
    EXPECTED_CORRECTIVE_TEXT,
    EXPECTED_CORRECTIVE_TEXT_SHA,
    EXPECTED_POSTED_AT_UTC,
    EXPECTED_SCREENSHOT_SHA256,
    EXPECTED_X_POST_ID,
    PAID_PARTNERSHIP_ATTESTATION,
    POST_VISIBLE_ATTESTATION,
    SCREENSHOT_SOURCE,
    TEXT_ATTESTATION,
    CorrectiveEvidenceError,
    parse_x_post_url,
    snowflake_timestamp_utc,
    validate_attestations,
    validate_screenshot_metadata,
)


def test_corrective_text_sha_is_fixed() -> None:
    assert hashlib.sha256(
        EXPECTED_CORRECTIVE_TEXT.encode(
            "utf-8"
        )
    ).hexdigest() == (
        EXPECTED_CORRECTIVE_TEXT_SHA
    )


def test_x_post_url_parse_passes() -> None:
    handle, post_id = parse_x_post_url(
        "https://x.com/mz_GK7_DM2/"
        "status/2078417820015333645"
    )

    assert handle == "@mz_GK7_DM2"
    assert post_id == EXPECTED_X_POST_ID


def test_invalid_x_post_url_fails() -> None:
    with pytest.raises(
        CorrectiveEvidenceError,
        match="format mismatch",
    ):
        parse_x_post_url(
            "https://example.com/post/1"
        )


def test_snowflake_timestamp_is_fixed() -> None:
    assert snowflake_timestamp_utc(
        EXPECTED_X_POST_ID
    ) == EXPECTED_POSTED_AT_UTC


def test_attestations_pass() -> None:
    validate_attestations(
        paid_partnership_attestation=(
            PAID_PARTNERSHIP_ATTESTATION
        ),
        text_attestation=(
            TEXT_ATTESTATION
        ),
        post_visible_attestation=(
            POST_VISIBLE_ATTESTATION
        ),
    )


def test_screenshot_metadata_passes() -> None:
    validate_screenshot_metadata(
        sha256=EXPECTED_SCREENSHOT_SHA256,
        width=598,
        height=373,
        source=SCREENSHOT_SOURCE,
    )

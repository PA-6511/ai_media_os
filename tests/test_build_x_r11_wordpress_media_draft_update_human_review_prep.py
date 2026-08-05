from __future__ import annotations

import hashlib

import pytest

from scripts.build_x_r11_wordpress_media_draft_update_human_review_prep import (
    EXPECTED_MEDIA_SHA,
    EXPECTED_MEDIA_ALT,
    MEDIA_URL_PLACEHOLDER,
    REMOTE_COVER_URL,
    MediaDraftUpdateReviewError,
    build_review_checklist,
    validate_content_preview,
    validate_local_media,
    validate_pending_checklist,
)


def test_ten_pending_checks_pass() -> None:
    validate_pending_checklist(
        build_review_checklist()
    )


def test_duplicate_check_id_fails() -> None:
    checklist = build_review_checklist()

    checklist[1]["check_id"] = (
        checklist[0]["check_id"]
    )

    with pytest.raises(
        MediaDraftUpdateReviewError,
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
        MediaDraftUpdateReviewError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_local_media_validation_passes(
    tmp_path,
) -> None:
    value = (
        b"\xff\xd8\xff"
        + b"fixed-test-image"
    )

    path = tmp_path / "cover.jpg"
    path.write_bytes(value)

    import scripts.build_x_r11_wordpress_media_draft_update_human_review_prep as module

    original_sha = module.EXPECTED_MEDIA_SHA

    try:
        module.EXPECTED_MEDIA_SHA = (
            hashlib.sha256(
                value
            ).hexdigest()
        )

        result = validate_local_media(
            path=path,
            expected_size=len(value),
        )

    finally:
        module.EXPECTED_MEDIA_SHA = (
            original_sha
        )

    assert result[
        "jpeg_magic_verified"
    ] is True


def test_content_preview_validation_passes(
    tmp_path,
) -> None:
    text = (
        '<figure class="ebook-cover-image">'
        f'<img src="{MEDIA_URL_PLACEHOLDER}" '
        f'alt="{EXPECTED_MEDIA_ALT}">'
        "</figure>"
    )

    assert REMOTE_COVER_URL not in text

    path = tmp_path / "preview.html"

    path.write_text(
        text,
        encoding="utf-8",
    )

    result = validate_content_preview(
        path=path,
        expected_sha256=(
            hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()
        ),
    )

    assert result[
        "media_url_placeholder_count"
    ] == 1

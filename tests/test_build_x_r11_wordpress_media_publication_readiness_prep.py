from __future__ import annotations

import hashlib

import pytest

from scripts.build_x_r11_wordpress_media_publication_readiness_prep import (
    MEDIA_FILENAME,
    MEDIA_URL_PLACEHOLDER,
    MediaReadinessError,
    REMOTE_COVER_URL,
    replace_remote_cover_url,
    validate_image_binary,
    validate_media_filename,
)


def test_media_filename_passes() -> None:
    validate_media_filename(
        MEDIA_FILENAME
    )


def test_invalid_media_filename_fails() -> None:
    with pytest.raises(
        MediaReadinessError,
        match="filename mismatch",
    ):
        validate_media_filename(
            "wrong.jpg"
        )


def test_jpeg_binary_passes_with_test_sha() -> None:
    value = (
        b"\xff\xd8\xff"
        + b"test-jpeg-content"
    )

    result = validate_image_binary(
        value,
        expected_sha256=(
            hashlib.sha256(
                value
            ).hexdigest()
        ),
    )

    assert result[
        "jpeg_magic_verified"
    ] is True


def test_non_jpeg_binary_fails() -> None:
    value = b"not-a-jpeg"

    with pytest.raises(
        MediaReadinessError,
        match="not a JPEG",
    ):
        validate_image_binary(
            value,
            expected_sha256=(
                hashlib.sha256(
                    value
                ).hexdigest()
            ),
        )


def test_remote_cover_replaced_once() -> None:
    source = (
        '<figure class="ebook-cover-image">'
        f'<img src="{REMOTE_COVER_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
    )

    result = replace_remote_cover_url(
        source
    )

    assert REMOTE_COVER_URL not in result

    assert result.count(
        MEDIA_URL_PLACEHOLDER
    ) == 1

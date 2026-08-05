from __future__ import annotations

import pytest

from scripts.build_x_r11_wordpress_draft_render_input_discovery import (
    RenderInputDiscoveryError,
    extract_image_candidates,
    inspect_image_bytes,
    score_candidate,
    validate_image_metadata,
)


def build_jpeg_header(
    *,
    width: int,
    height: int,
) -> bytes:
    return (
        b"\xff\xd8"
        b"\xff\xc0"
        b"\x00\x11"
        b"\x08"
        + height.to_bytes(
            2,
            "big",
        )
        + width.to_bytes(
            2,
            "big",
        )
        + b"\x03"
        + b"\x01\x11\x00"
        + b"\x02\x11\x00"
        + b"\x03\x11\x00"
        + b"\xff\xd9"
    )


def test_target_cover_candidate_receives_strong_score() -> None:
    candidate = {
        "url": (
            "https://tshop.r10s.jp/"
            "rakutenkobo-ebooks/cabinet/"
            "6437/2000020786437.jpg"
        ),
        "alt": "のあ先輩はともだち。11",
        "sources": [
            "img:src"
        ],
    }

    result = score_candidate(
        candidate,
        expected_title=(
            "のあ先輩はともだち。"
        ),
        expected_volume_number="11",
    )

    assert result[
        "strong_identity_signal"
    ] is True

    assert result[
        "official_image_host"
    ] is True

    assert result[
        "product_cabinet_path"
    ] is True

    assert result[
        "candidate_score"
    ] >= 800


def test_wrong_volume_is_not_strong_identity() -> None:
    candidate = {
        "url": (
            "https://tshop.r10s.jp/"
            "rakutenkobo-ebooks/cabinet/"
            "0000/wrong.jpg"
        ),
        "alt": "のあ先輩はともだち。10",
        "sources": [
            "img:src"
        ],
    }

    result = score_candidate(
        candidate,
        expected_title=(
            "のあ先輩はともだち。"
        ),
        expected_volume_number="11",
    )

    assert result[
        "title_match"
    ] is True

    assert result[
        "volume_match"
    ] is False

    assert result[
        "strong_identity_signal"
    ] is False


def test_html_image_candidates_are_deduplicated() -> None:
    page_html = """
    <html>
      <head>
        <meta
          property="og:image"
          content="/cover.jpg"
        >
      </head>
      <body>
        <img
          src="/cover.jpg"
          alt="のあ先輩はともだち。11"
        >
      </body>
    </html>
    """

    candidates = extract_image_candidates(
        page_html,
        base_url=(
            "https://books.rakuten.co.jp/"
            "rk/example/"
        ),
    )

    assert len(candidates) == 1

    assert candidates[0]["url"] == (
        "https://books.rakuten.co.jp/"
        "cover.jpg"
    )

    assert candidates[0]["alt"] == (
        "のあ先輩はともだち。11"
    )

    assert set(
        candidates[0]["sources"]
    ) == {
        "meta:og:image",
        "img:src",
    }


def test_jpeg_dimensions_are_parsed() -> None:
    data = build_jpeg_header(
        width=300,
        height=373,
    )

    metadata = inspect_image_bytes(
        data,
        content_type="image/jpeg",
    )

    assert metadata["format"] == "jpeg"
    assert metadata["width"] == 300
    assert metadata["height"] == 373


def test_small_cover_image_is_rejected() -> None:
    metadata = {
        "width": 120,
        "height": 160,
    }

    with pytest.raises(
        RenderInputDiscoveryError,
        match="width is too small",
    ):
        validate_image_metadata(
            metadata
        )

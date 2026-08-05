from __future__ import annotations

from scripts.build_x_r11_wordpress_draft_render_input_discovery import (
    IMAGE_FETCH_TIMEOUT_SECONDS,
    MAX_IMAGE_FETCH_ATTEMPTS,
    select_image_fetch_candidates,
)


def make_candidate(
    index: int,
    *,
    score: int,
    strong: bool,
    allowed: bool = True,
    bad_path: bool = False,
) -> dict:
    return {
        "url": (
            "https://tshop.r10s.jp/"
            "rakutenkobo-ebooks/cabinet/"
            f"{index}.jpg"
        ),
        "official_image_host": allowed,
        "bad_path_token_found": bad_path,
        "candidate_score": score,
        "strong_identity_signal": strong,
    }


def test_network_limits_are_fixed() -> None:
    assert IMAGE_FETCH_TIMEOUT_SECONDS == 8
    assert MAX_IMAGE_FETCH_ATTEMPTS == 4


def test_candidate_count_is_limited_to_four() -> None:
    candidates = [
        make_candidate(
            index,
            score=100 + index,
            strong=False,
        )
        for index in range(12)
    ]

    selected = select_image_fetch_candidates(
        candidates
    )

    assert len(selected) == 4


def test_strong_identity_candidates_are_prioritized() -> None:
    candidates = [
        make_candidate(
            1,
            score=900,
            strong=False,
        ),
        make_candidate(
            2,
            score=500,
            strong=True,
        ),
        make_candidate(
            3,
            score=400,
            strong=True,
        ),
        make_candidate(
            4,
            score=800,
            strong=False,
        ),
    ]

    selected = select_image_fetch_candidates(
        candidates
    )

    assert selected[0][
        "strong_identity_signal"
    ] is True

    assert selected[1][
        "strong_identity_signal"
    ] is True


def test_invalid_candidates_are_removed() -> None:
    candidates = [
        make_candidate(
            1,
            score=900,
            strong=True,
            allowed=False,
        ),
        make_candidate(
            2,
            score=800,
            strong=True,
            bad_path=True,
        ),
        make_candidate(
            3,
            score=700,
            strong=True,
        ),
    ]

    selected = select_image_fetch_candidates(
        candidates
    )

    assert len(selected) == 1

    assert selected[0]["url"].endswith(
        "/3.jpg"
    )

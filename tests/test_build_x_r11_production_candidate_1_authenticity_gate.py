from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_x_r11_production_candidate_1_authenticity_gate import (
    XR11CandidateAuthenticityError,
    run_authenticity_gate,
)


def write_source(
    path: Path,
    candidates: list[dict],
) -> None:
    path.write_text(
        json.dumps(
            {
                "phase": (
                    "X-R11-PRODUCTION-CANDIDATE-1-"
                    "SOURCE-DETAIL"
                ),
                "status": (
                    "PASS_PRODUCTION_SOURCE_DETAIL_"
                    "READY_NO_EXECUTION"
                ),
                "database_scope": (
                    "PRODUCTION_READ_ONLY"
                ),
                "source_database_unchanged": True,
                "database_write": False,
                "production_status": "NO_GO",
                "candidate_details": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def candidate(
    *,
    title: str,
    url: str | None,
    wordpress_post_id: int | None,
    wordpress_status: str,
) -> dict:
    return {
        "ebook_item_id": title,
        "title": title,
        "release_date": "2026-07-17",
        "wordpress_post_id": (
            wordpress_post_id
        ),
        "wordpress_status": (
            wordpress_status
        ),
        "excluded": 0,
        "store_offers": [
            {
                "store": "rakuten_kobo",
                "url": url,
            }
        ],
    }


def run_gate(
    tmp_path: Path,
    candidates: list[dict],
    name: str,
) -> dict:
    source = tmp_path / f"{name}.json"
    write_source(source, candidates)

    return run_authenticity_gate(
        source_detail_path=source,
        output_root=tmp_path / f"{name}_out",
    )


def test_sample_without_url_is_rejected(
    tmp_path: Path,
) -> None:
    result = run_gate(
        tmp_path,
        [
            candidate(
                title="サンプル作品",
                url=None,
                wordpress_post_id=None,
                wordpress_status="NOT_CREATED",
            )
        ],
        "sample",
    )

    assert result["status"] == (
        "PASS_AUTHENTICITY_GATE_"
        "NO_AUTHENTIC_PRODUCTION_CANDIDATE"
    )
    assert result[
        "authentic_candidate_count"
    ] == 0


def test_test_title_and_example_url_are_rejected(
    tmp_path: Path,
) -> None:
    result = run_gate(
        tmp_path,
        [
            candidate(
                title="テストコミック 第1巻",
                url=(
                    "https://example.com/"
                    "affiliate/1"
                ),
                wordpress_post_id=None,
                wordpress_status="NOT_CREATED",
            )
        ],
        "test_placeholder",
    )

    assert result[
        "authentic_candidate_count"
    ] == 0


def test_authentic_source_without_draft_is_reported(
    tmp_path: Path,
) -> None:
    result = run_gate(
        tmp_path,
        [
            candidate(
                title="実在作品 第1巻",
                url=(
                    "https://books.rakuten.co.jp/"
                    "rb/12345678/"
                ),
                wordpress_post_id=None,
                wordpress_status="NOT_CREATED",
            )
        ],
        "authentic_no_draft",
    )

    assert result["status"] == (
        "PASS_AUTHENTICITY_GATE_"
        "AUTHENTIC_SOURCE_NOT_DRAFT_READY"
    )
    assert result[
        "authentic_candidate_count"
    ] == 1
    assert result[
        "wordpress_draft_ready_candidate_count"
    ] == 0


def test_one_draft_ready_requires_human_review(
    tmp_path: Path,
) -> None:
    result = run_gate(
        tmp_path,
        [
            candidate(
                title="実在作品 第1巻",
                url=(
                    "https://books.rakuten.co.jp/"
                    "rb/12345678/"
                ),
                wordpress_post_id=123,
                wordpress_status="DRAFT",
            )
        ],
        "draft_ready",
    )

    assert result["status"] == (
        "PASS_AUTHENTICITY_GATE_"
        "ONE_DRAFT_READY_CANDIDATE_"
        "HUMAN_REVIEW_REQUIRED"
    )
    assert result[
        "wordpress_draft_ready_candidate_count"
    ] == 1
    assert result[
        "candidate_selected"
    ] is False


def test_invalid_source_status_is_rejected(
    tmp_path: Path,
) -> None:
    source = tmp_path / "invalid.json"

    source.write_text(
        json.dumps(
            {
                "phase": (
                    "X-R11-PRODUCTION-CANDIDATE-1-"
                    "SOURCE-DETAIL"
                ),
                "status": "INVALID",
                "database_scope": (
                    "PRODUCTION_READ_ONLY"
                ),
                "source_database_unchanged": True,
                "database_write": False,
                "production_status": "NO_GO",
                "candidate_details": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11CandidateAuthenticityError,
        match="source detail status is invalid",
    ):
        run_authenticity_gate(
            source_detail_path=source,
            output_root=tmp_path / "invalid_out",
        )

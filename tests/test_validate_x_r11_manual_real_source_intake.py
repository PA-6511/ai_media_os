from __future__ import annotations

import csv
from pathlib import Path

from scripts.validate_x_r11_manual_real_source_intake import (
    validate_manual_intake,
)


POLICY_PATH = (
    Path.cwd()
    / "config/x_r11_manual_real_source_intake_policy.json"
)

HEADER = [
    "intake_id",
    "title",
    "volume_label",
    "release_date",
    "publisher",
    "authors",
    "category",
    "source_discovery_url",
    "publisher_confirmation_url",
    "amazon_url",
    "rakuten_kobo_url",
    "dmm_url",
    "description_mode",
    "human_review_state",
]


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=HEADER,
        )
        writer.writeheader()
        writer.writerows(rows)


def valid_row() -> dict[str, str]:
    return {
        "intake_id": "real-20260718-001",
        "title": "実在作品 第1巻",
        "volume_label": "第1巻",
        "release_date": "2026-07-18",
        "publisher": "実在出版社",
        "authors": "著者名",
        "category": "comic",
        "source_discovery_url": (
            "https://books.rakuten.co.jp/"
            "rb/12345678/"
        ),
        "publisher_confirmation_url": (
            "https://www.kadokawa.co.jp/"
            "product/322601000001/"
        ),
        "amazon_url": "",
        "rakuten_kobo_url": (
            "https://books.rakuten.co.jp/"
            "rb/12345678/"
        ),
        "dmm_url": "",
        "description_mode": "MINIMAL",
        "human_review_state": (
            "NOT_REVIEWED"
        ),
    }


def run_validation(
    tmp_path: Path,
    rows: list[dict[str, str]],
    name: str,
) -> dict:
    csv_path = tmp_path / f"{name}.csv"
    write_csv(csv_path, rows)

    return validate_manual_intake(
        input_csv_path=csv_path,
        policy_path=POLICY_PATH,
        output_root=tmp_path / f"{name}_out",
    )


def test_empty_template_is_ready(
    tmp_path: Path,
) -> None:
    result = run_validation(
        tmp_path,
        [],
        "empty",
    )

    assert result["status"] == (
        "PASS_MANUAL_REAL_SOURCE_INTAKE_"
        "TEMPLATE_READY_NO_EXECUTION"
    )
    assert result["input_row_count"] == 0
    assert result[
        "database_import_allowed"
    ] is False


def test_one_valid_candidate_requires_review(
    tmp_path: Path,
) -> None:
    result = run_validation(
        tmp_path,
        [valid_row()],
        "valid",
    )

    assert result["status"] == (
        "PASS_MANUAL_REAL_SOURCE_INTAKE_"
        "ONE_VALID_CANDIDATE_REVIEW_REQUIRED"
    )
    assert result[
        "valid_candidate_count"
    ] == 1
    assert result[
        "human_review_required"
    ] is True
    assert result[
        "database_import_allowed"
    ] is False


def test_synthetic_title_is_blocked(
    tmp_path: Path,
) -> None:
    row = valid_row()
    row["title"] = "テストコミック 第1巻"

    result = run_validation(
        tmp_path,
        [row],
        "synthetic",
    )

    blockers = result[
        "candidate_assessments"
    ][0]["blockers"]

    assert result["status"] == (
        "BLOCKED_MANUAL_REAL_SOURCE_INTAKE_"
        "INVALID_CANDIDATE"
    )
    assert (
        "SYNTHETIC_TITLE_FORBIDDEN"
        in blockers
    )


def test_placeholder_url_is_blocked(
    tmp_path: Path,
) -> None:
    row = valid_row()
    row["rakuten_kobo_url"] = (
        "https://example.com/item/1"
    )

    result = run_validation(
        tmp_path,
        [row],
        "placeholder",
    )

    blockers = result[
        "candidate_assessments"
    ][0]["blockers"]

    assert any(
        "PLACEHOLDER_URL" in blocker
        for blocker in blockers
    )


def test_multiple_rows_are_blocked(
    tmp_path: Path,
) -> None:
    first = valid_row()
    second = valid_row()
    second["intake_id"] = (
        "real-20260718-002"
    )
    second["title"] = "実在作品 第2巻"

    result = run_validation(
        tmp_path,
        [first, second],
        "multiple",
    )

    assert result["status"] == (
        "BLOCKED_MANUAL_REAL_SOURCE_INTAKE_"
        "ROW_LIMIT_EXCEEDED"
    )
    assert result[
        "automatic_selection_allowed"
    ] is False

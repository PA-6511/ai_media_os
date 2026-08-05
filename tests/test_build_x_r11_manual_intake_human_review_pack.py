from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from scripts.build_x_r11_manual_intake_human_review_pack import (
    CSV_HEADER,
    EXPECTED_MANIFEST_PHASE,
    EXPECTED_MANIFEST_STATUS,
    EXPECTED_VALIDATION_PHASE,
    EXPECTED_VALIDATION_STATUS,
    XR11HumanReviewPackError,
    run_human_review_pack,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def candidate() -> dict[str, str]:
    return {
        "intake_id": (
            "x-r11-real-20260717-noa-senpai-11"
        ),
        "title": "のあ先輩はともだち。",
        "volume_label": "第11巻",
        "release_date": "2026-07-17",
        "publisher": "集英社",
        "authors": "あきやまえんま",
        "category": "comic",
        "source_discovery_url": (
            "https://books.rakuten.co.jp/"
            "rk/real-item/"
        ),
        "publisher_confirmation_url": (
            "https://www.shueisha.co.jp/"
            "books/items/real-item"
        ),
        "amazon_url": "",
        "rakuten_kobo_url": (
            "https://books.rakuten.co.jp/"
            "rk/real-item/"
        ),
        "dmm_url": "",
        "description_mode": "MINIMAL",
        "human_review_state": "NOT_REVIEWED",
    }


def prepare_files(
    tmp_path: Path,
) -> dict[str, Path]:
    row = candidate()

    input_csv = tmp_path / "input.csv"

    with input_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_HEADER,
        )
        writer.writeheader()
        writer.writerow(row)

    policy = {
        "phase": (
            "X-R11-MANUAL-REAL-SOURCE-INTAKE-PREP"
        ),
        "status": (
            "MANUAL_REAL_SOURCE_INTAKE_POLICY_FIXED"
        ),
        "version": 1,
    }

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(policy),
        encoding="utf-8",
    )

    candidate_digest = canonical_digest(
        row
    )
    policy_digest = canonical_digest(
        policy
    )

    validation = {
        "phase": EXPECTED_VALIDATION_PHASE,
        "status": EXPECTED_VALIDATION_STATUS,
        "policy_digest_sha256": policy_digest,
        "valid_candidate_count": 1,
        "candidate_assessments": [
            {
                "candidate": row,
                "candidate_digest_sha256": (
                    candidate_digest
                ),
                "valid": True,
                "blockers": [],
            }
        ],
        "candidate_selected": False,
        "database_import_allowed": False,
        "production_status": "NO_GO",
    }

    validation_path = (
        tmp_path / "validation.json"
    )
    validation_path.write_text(
        json.dumps(validation),
        encoding="utf-8",
    )

    manifest = {
        "phase": EXPECTED_MANIFEST_PHASE,
        "status": EXPECTED_MANIFEST_STATUS,
        "row_entered": True,
        "input_csv_current_sha256": (
            sha256_file(input_csv)
        ),
        "policy_snapshot_sha256": (
            sha256_file(policy_path)
        ),
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "candidate_selected": False,
        "database_import_allowed": False,
        "wordpress_draft_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "production_status": "NO_GO",
    }

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    database_path = tmp_path / "production.db"

    connection = sqlite3.connect(
        database_path
    )

    try:
        connection.executescript(
            """
            CREATE TABLE ebook_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                release_date TEXT NOT NULL,
                publisher TEXT,
                wordpress_post_id INTEGER,
                wordpress_status TEXT,
                excluded INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE store_offers (
                id TEXT PRIMARY KEY,
                ebook_item_id TEXT NOT NULL,
                store TEXT,
                product_url TEXT
            );
            """
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "input_csv": input_csv,
        "policy": policy_path,
        "manifest": manifest_path,
        "validation": validation_path,
        "database": database_path,
    }


def run_pack(
    tmp_path: Path,
    files: dict[str, Path],
    output_name: str,
) -> dict:
    return run_human_review_pack(
        input_csv_path=files["input_csv"],
        policy_path=files["policy"],
        manifest_path=files["manifest"],
        validation_result_path=(
            files["validation"]
        ),
        production_database_path=(
            files["database"]
        ),
        expected_production_database_path=(
            files["database"]
        ),
        output_root=(
            tmp_path / output_name
        ),
    )


def test_valid_candidate_awaits_approval(
    tmp_path: Path,
) -> None:
    files = prepare_files(tmp_path)

    result = run_pack(
        tmp_path,
        files,
        "valid",
    )

    assert result["status"] == (
        "PASS_HUMAN_REVIEW_PACK_READY_"
        "AWAITING_EXPLICIT_APPROVAL"
    )
    assert result[
        "duplicate_match_count"
    ] == 0
    assert result[
        "approval_issued"
    ] is False
    assert result[
        "database_import_allowed"
    ] is False


def test_duplicate_book_is_blocked(
    tmp_path: Path,
) -> None:
    files = prepare_files(tmp_path)

    connection = sqlite3.connect(
        files["database"]
    )

    try:
        connection.execute(
            """
            INSERT INTO ebook_items (
                id,
                title,
                release_date,
                publisher
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "existing-1",
                "のあ先輩はともだち。",
                "2026-07-17",
                "集英社",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    result = run_pack(
        tmp_path,
        files,
        "duplicate_book",
    )

    assert result["status"] == (
        "BLOCKED_HUMAN_REVIEW_PACK_"
        "DUPLICATE_FOUND"
    )
    assert result[
        "book_duplicate_match_count"
    ] == 1


def test_duplicate_url_is_blocked(
    tmp_path: Path,
) -> None:
    files = prepare_files(tmp_path)

    connection = sqlite3.connect(
        files["database"]
    )

    try:
        connection.execute(
            """
            INSERT INTO store_offers (
                id,
                ebook_item_id,
                store,
                product_url
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "offer-1",
                "existing-1",
                "rakuten_kobo",
                (
                    "https://books.rakuten.co.jp/"
                    "rk/real-item/"
                ),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    result = run_pack(
        tmp_path,
        files,
        "duplicate_url",
    )

    assert result["status"] == (
        "BLOCKED_HUMAN_REVIEW_PACK_"
        "DUPLICATE_FOUND"
    )
    assert result[
        "url_duplicate_match_count"
    ] == 1


def test_tampered_csv_is_rejected(
    tmp_path: Path,
) -> None:
    files = prepare_files(tmp_path)

    files["input_csv"].write_text(
        "tampered\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11HumanReviewPackError,
        match="header",
    ):
        run_pack(
            tmp_path,
            files,
            "tampered",
        )


def test_invalid_manifest_state_is_rejected(
    tmp_path: Path,
) -> None:
    files = prepare_files(tmp_path)

    manifest = json.loads(
        files["manifest"].read_text(
            encoding="utf-8"
        )
    )
    manifest["status"] = "INVALID"

    files["manifest"].write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11HumanReviewPackError,
        match="manifest status is invalid",
    ):
        run_pack(
            tmp_path,
            files,
            "invalid_manifest",
        )

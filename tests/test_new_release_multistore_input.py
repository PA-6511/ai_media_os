from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.new_release_multistore_input import (
    ImportArtifactConflictError,
    SCHEMA_ID,
    build_store_buttons_html,
    import_multistore_csv,
    safe_filename,
    write_import_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "import_new_release_multistore_v2.py"


def write_csv(path: Path, rows: list[dict[str, str]], *, bom: bool = False) -> Path:
    fieldnames = list(rows[0].keys())
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def base_row(**overrides: str) -> dict[str, str]:
    row = {
        "batch_id": "batch-001",
        "item_id": "item-001",
        "title": "新刊コミック 第1巻",
        "display_title": "新刊コミック 第1巻",
        "volume_label": "第1巻",
        "release_date": "2026-07-13",
        "category": "コミック",
        "rakuten_kobo_url": "https://books.rakuten.co.jp/rb/12345678/",
        "image_url": "https://example.com/images/cover.jpg",
        "image_alt": "新刊コミック 第1巻 カバー",
        "wordpress_status": "draft",
        "schema_id": SCHEMA_ID,
        "record_status": "READY_FOR_DRAFT",
        "publish_ready": "true",
        "pr_required": "true",
        "price_notice_required": "true",
        "dmm_match_status": "",
        "amazon_match_status": "",
        "source_row_sha256": "abc123def456",
        "available_store_count": "",
        "edition_type": "volume",
        "publisher": "テスト出版",
        "authors": "著者A|著者B",
        "series": "テストシリーズ",
        "item_number": "item-number-1",
        "isbn13": "9781234567890",
        "dmm_item_url": "",
        "dmm_affiliate_url": "",
        "dmm_content_id": "",
        "dmm_price_yen": "",
        "amazon_asin": "",
        "amazon_item_url": "",
        "amazon_affiliate_url": "",
        "amazon_price_yen": "",
    }
    row.update(overrides)
    return row


def import_rows(tmp_path: Path, rows: list[dict[str, str]], *, bom: bool = False) -> dict:
    csv_path = write_csv(tmp_path / "input.csv", rows, bom=bom)
    return import_multistore_csv(csv_path)


def test_kobo_only_row_passes_and_wordpress_is_locked(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row()])

    assert result["status"] == "PASS_WITH_WARNINGS"
    assert result["ready_count"] == 1
    assert result["blocked_count"] == 0
    payload = result["ready_payloads"][0]
    assert payload["wordpress"]["status"] == "draft"
    assert payload["wordpress"]["write_allowed"] is False
    assert payload["wordpress"]["publish_allowed"] is False
    assert payload["available_store_count"] == 1
    assert payload["store_navigation"][0]["key"] == "rakuten_kobo"
    assert payload["safety"]["external_network_performed"] is False
    assert payload["safety"]["wordpress_write_performed"] is False
    assert payload["safety"]["wordpress_publish_performed"] is False


def test_kobo_canonical_metadata_and_verification_evidence_are_preserved(
    tmp_path: Path,
) -> None:
    result = import_rows(
        tmp_path,
        [
            base_row(
                authors="",
                author_name="原作：著者A|作画：著者B|原作：著者A",
                publisher="",
                publisher_name="A&amp;B   出版",
                verified_at="2026-08-01T09:00:00+09:00",
                verification_method="RAKUTEN_KOBO_API_RESPONSE",
            )
        ],
    )
    payload = result["ready_payloads"][0]
    offer = payload["store_navigation"][0]
    assert payload["authors"] == ["原作：著者A", "作画：著者B"]
    assert payload["publisher"] == "A&B 出版"
    assert offer["verified_at"] == "2026-08-01T09:00:00+09:00"
    assert offer["verification_method"] == "RAKUTEN_KOBO_API_RESPONSE"
    assert offer["source_row_sha256"] == "abc123def456"
    assert payload["source_evidence"]["source_row_sha256"] == "abc123def456"


def test_cta_rel_attributes_are_applied() -> None:
    html_output = build_store_buttons_html(
        [{"key": "rakuten_kobo", "label": "楽天Koboで確認", "url": "https://example.com/kobo"}]
    )

    assert 'rel="nofollow sponsored noopener"' in html_output
    assert 'target="_blank"' in html_output
    assert 'class="ebook-store-button affiliate-cta store-rakuten_kobo"' in html_output


def test_unverified_dmm_url_is_blocked(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [base_row(dmm_item_url="https://book.dmm.com/product/123/", dmm_match_status="REVIEW_REQUIRED")],
    )

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "DMM_URL_WITH_UNVERIFIED_STATUS"


def test_dmm_latest_url_is_blocked(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [base_row(dmm_item_url="https://book.dmm.com/latest/", dmm_match_status="MANUAL_VERIFIED")],
    )

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "DMM_LATEST_URL_FORBIDDEN"


def test_verified_dmm_url_is_adopted(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [base_row(dmm_affiliate_url="https://book.dmm.com/product/123/?aff=1", dmm_match_status="MANUAL_VERIFIED_OK")],
    )

    payload = result["ready_payloads"][0]
    keys = [store["key"] for store in payload["store_navigation"]]
    assert keys == ["rakuten_kobo", "dmm_books"]
    assert payload["available_store_count"] == 2


def test_invalid_amazon_asin_is_blocked(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(amazon_asin="BAD")])

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "AMAZON_ASIN_INVALID"


def test_unverified_amazon_url_is_blocked(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [base_row(amazon_item_url="https://www.amazon.co.jp/dp/B012345678", amazon_match_status="REVIEW_REQUIRED")],
    )

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "AMAZON_URL_WITH_UNVERIFIED_STATUS"


def test_amazon_can_be_omitted_with_warning(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(amazon_match_status="MANUAL_ASIN_REQUIRED")])

    assert result["ready_count"] == 1
    assert result["warning_count"] == 1
    assert result["warnings"][0]["code"] == "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION"


def test_amazon_not_found_remains_importable_without_fake_link_or_asin(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(amazon_match_status="NOT_FOUND")])

    assert result["ready_count"] == 1
    assert result["blocked_count"] == 0
    assert result["warning_count"] == 1
    assert result["warnings"][0]["code"] == "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION"
    payload = result["ready_payloads"][0]
    assert "amazon_asin" not in payload["identifiers"]
    assert all(store["key"] != "amazon_kindle" for store in payload["store_navigation"])


def test_single_episode_is_blocked(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(edition_type="single_episode")])

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "SINGLE_EPISODE_FORBIDDEN"


def test_available_store_count_mismatch_is_blocked(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(available_store_count="2")])

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "AVAILABLE_STORE_COUNT_MISMATCH"


def test_utf8_bom_csv_is_supported(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row()], bom=True)

    assert result["ready_count"] == 1


def test_artifacts_are_written_under_tmp_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    result = import_rows(tmp_path, [base_row(), base_row(item_id="item-002", title="別作品", source_row_sha256="def789")])

    artifacts = write_import_artifacts(result, repo_root)

    item_paths = artifacts["item_paths"]
    assert len(item_paths) == 2
    first_item = Path(item_paths[0])
    assert first_item.exists()
    payload = json.loads(first_item.read_text(encoding="utf-8"))
    assert payload["content_item_id"] == "item-001"

    manifest_path = Path(artifacts["manifest_records"][0]["manifest_path"])
    blocked_path = Path(artifacts["blocked_records"][0]["blocked_path"])
    result_log_path = Path(artifacts["result_log_records"][0]["result_log_path"])
    assert manifest_path.exists()
    assert blocked_path.exists()
    assert result_log_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    blocked = json.loads(blocked_path.read_text(encoding="utf-8"))
    result_log = json.loads(result_log_path.read_text(encoding="utf-8"))
    assert manifest["status"] == result["status"]
    assert blocked["status"] == result["status"]
    assert result_log["status"] == result["status"]
    assert manifest["safety"]["external_network_performed"] is False
    assert blocked["safety"]["wordpress_write_performed"] is False
    assert result_log["safety"]["wordpress_publish_performed"] is False


def test_realistic_466_ready_39_blocked_batch_preserves_warnings_and_artifacts(
    tmp_path: Path,
) -> None:
    ready_rows = [
        base_row(
            item_id=f"ready-{index:03d}",
            title=f"新刊コミック 第{index}巻",
            source_row_sha256=f"ready-sha-{index:03d}",
            item_number=f"ready-number-{index:03d}",
            isbn13="",
            amazon_match_status="NOT_FOUND",
        )
        for index in range(466)
    ]
    blocked_rows = [
        base_row(
            item_id=f"blocked-{index:03d}",
            title=f"単話 {index}",
            source_row_sha256=f"blocked-sha-{index:03d}",
            item_number=f"blocked-number-{index:03d}",
            isbn13="",
            edition_type="single_episode",
            amazon_match_status="NOT_FOUND",
        )
        for index in range(39)
    ]

    result = import_rows(tmp_path, ready_rows + blocked_rows, bom=True)

    assert result["ready_count"] == 466
    assert result["blocked_count"] == 39
    assert result["warning_count"] == 466
    assert all(
        warning["code"] == "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION"
        for warning in result["warnings"]
    )
    assert all(
        "amazon_asin" not in payload["identifiers"]
        for payload in result["ready_payloads"]
    )

    artifacts = write_import_artifacts(result, tmp_path / "repo")

    assert len(artifacts["item_paths"]) == 466
    assert artifacts["ready_count"] == 466
    assert artifacts["blocked_count"] == 39
    assert artifacts["warning_count"] == 466
    manifest = artifacts["manifest_records"][0]
    blocked = artifacts["blocked_records"][0]
    result_log = artifacts["result_log_records"][0]
    assert len(manifest["item_paths"]) == 466
    assert len(blocked["blocked_rows"]) == 39
    assert result_log["warning_count"] == 466


def test_complete_batch_conflict_is_classified_without_overwrite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    result = import_rows(tmp_path, [base_row(amazon_match_status="NOT_FOUND")])
    first = write_import_artifacts(result, repo_root)
    manifest_path = Path(first["manifest_records"][0]["manifest_path"])
    before = manifest_path.read_bytes()

    with pytest.raises(ImportArtifactConflictError) as caught:
        write_import_artifacts(result, repo_root)

    assert caught.value.state == "complete"
    assert caught.value.batch_ids == ["batch-001"]
    assert manifest_path.read_bytes() == before


def test_partial_batch_conflict_is_classified_without_overwrite(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    result = import_rows(tmp_path, [base_row(amazon_match_status="NOT_FOUND")])
    partial_dir = (
        repo_root
        / "exchange"
        / "inputs"
        / "new_release"
        / "batches"
        / "batch-001"
    )
    partial_dir.mkdir(parents=True)

    with pytest.raises(ImportArtifactConflictError) as caught:
        write_import_artifacts(result, repo_root)

    assert caught.value.state == "partial"
    assert caught.value.batch_ids == ["batch-001"]
    assert list(partial_dir.iterdir()) == []


def test_corrupt_nominally_complete_batch_is_classified_as_partial(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    result = import_rows(tmp_path, [base_row(amazon_match_status="NOT_FOUND")])
    first = write_import_artifacts(result, repo_root)
    manifest_path = Path(first["manifest_records"][0]["manifest_path"])
    manifest_path.write_text("{truncated", encoding="utf-8")

    with pytest.raises(ImportArtifactConflictError) as caught:
        write_import_artifacts(result, repo_root)

    assert caught.value.state == "partial"
    assert manifest_path.read_text(encoding="utf-8") == "{truncated"


def test_path_traversal_is_sanitized(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    result = import_rows(tmp_path, [base_row(item_id="../evil")])

    artifacts = write_import_artifacts(result, repo_root)
    assert any("evil.input.json" in path for path in artifacts["item_paths"])
    assert safe_filename("../evil") == "evil"


def test_html_special_characters_are_escaped(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [
            base_row(
                title='危険 <script>alert("x")</script>',
                image_alt='alt "quote" <tag>',
                rakuten_kobo_url="https://example.com/?q=<unsafe>",
            )
        ],
    )

    html_output = result["ready_payloads"][0]["store_buttons_html"]
    payload = result["ready_payloads"][0]
    assert "<script>" not in html_output
    assert "&lt;unsafe&gt;" in html_output
    assert payload["cover_image"]["alt"] == 'alt "quote" <tag>'


def test_javascript_url_is_rejected(tmp_path: Path) -> None:
    result = import_rows(tmp_path, [base_row(rakuten_kobo_url="javascript:alert(1)")])

    assert result["blocked_count"] == 1
    assert result["blocked_rows"][0]["error"]["code"] == "URL_SCHEME_FORBIDDEN"


def test_one_invalid_row_does_not_block_other_ready_rows(tmp_path: Path) -> None:
    result = import_rows(
        tmp_path,
        [
            base_row(item_id="item-001"),
            base_row(item_id="item-002", amazon_asin="BAD"),
            base_row(item_id="item-003", amazon_match_status="MANUAL_ASIN_REQUIRED"),
        ],
    )

    assert result["ready_count"] == 2
    assert result["blocked_count"] == 1
    assert result["warning_count"] == 2


def test_cli_strict_returns_exit_code_3_with_blocked_rows(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "strict.csv", [base_row(amazon_asin="BAD")])
    repo_root = tmp_path / "repo"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(csv_path), "--repo-root", str(repo_root), "--strict"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 3
    output = json.loads(completed.stdout)
    assert output["blocked_count"] == 1

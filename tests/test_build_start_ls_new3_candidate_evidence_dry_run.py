from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = "scripts/build_start_ls_new3_candidate_evidence_dry_run.py"
PASSED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION"
FAILED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_FAILED_NO_EXECUTION"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-3",
        "execution_mode": "CANDIDATE_EVIDENCE_DRY_RUN_ONLY_NO_EXTERNAL_FETCH",
    }


def _base_schema() -> dict:
    return {
        "schema_name": "START_LS_NEW3_CANDIDATE_EVIDENCE_SCHEMA",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-3",
    }


def _base_ls_new2_result() -> dict:
    return {
        "status": "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION",
        "ready_for_ls_new_3": True,
        "execution_allowed": False,
        "missing_required_human_fields": [],
    }


def _base_ls_new2_validation() -> dict:
    return {
        "validation_status": "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"
    }


def _base_filled_record() -> dict:
    return {
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "label": "ヤンマガKCスペシャル",
        "release_date": "2026-07-06",
        "ebook_release_date": "2026-07-06",
        "paper_release_date": "2026-07-06",
        "candidate_source_type": "publisher_official",
        "publisher_source_url": "https://www.kodansha.co.jp/comic/products/0000428841",
        "kindle_url": "https://www.amazon.co.jp/dp/B0H6DQLPPB",
        "rakuten_kobo_url": "https://books.rakuten.co.jp/rk/example",
        "dmm_books_url": "https://book.dmm.com/product/4071859/latest/",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "asin": "B0H6DQLPPB",
        "isbn": "978-4065442296",
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "schema": tmp_path / "config/schema.json",
        "ls2_result": tmp_path / "exchange/runtime/ls2_result.json",
        "ls2_validation": tmp_path / "exchange/logs/ls2_validation.json",
        "filled": tmp_path / "exchange/new_release/filled.json",
        "evidence": tmp_path / "exchange/new_release/evidence.json",
        "inventory": tmp_path / "exchange/new_release/source_inventory.json",
        "slots": tmp_path / "exchange/new_release/store_slots.json",
        "xpreview": tmp_path / "exchange/new_release/x_preview.json",
        "wppreview": tmp_path / "exchange/new_release/wp_preview.md",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "report": tmp_path / "reports/report.md",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["schema"], _base_schema())
    _write_json(paths["ls2_result"], _base_ls_new2_result())
    _write_json(paths["ls2_validation"], _base_ls_new2_validation())
    _write_json(paths["filled"], _base_filled_record())
    return paths


def _flags() -> list[str]:
    return [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]


def _run(paths: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    if flags is None:
        flags = _flags()

    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--schema",
        str(paths["schema"]),
        "--ls-new2-fill-result",
        str(paths["ls2_result"]),
        "--ls-new2-fill-validation-result",
        str(paths["ls2_validation"]),
        "--filled-candidate-record",
        str(paths["filled"]),
        "--output-evidence",
        str(paths["evidence"]),
        "--output-source-inventory",
        str(paths["inventory"]),
        "--output-store-slots",
        str(paths["slots"]),
        "--output-x-preview",
        str(paths["xpreview"]),
        "--output-wp-preview",
        str(paths["wppreview"]),
        "--output",
        str(paths["result"]),
        "--lock-output",
        str(paths["lock"]),
        "--report",
        str(paths["report"]),
    ] + flags

    return subprocess.run(cmd, text=True, capture_output=True, check=False)


@pytest.mark.parametrize(
    "missing_key",
    [
        "policy",
        "schema",
        "ls2_result",
        "ls2_validation",
        "filled",
    ],
)
def test_missing_required_input_file_failed(tmp_path: Path, missing_key: str) -> None:
    paths = _prepare(tmp_path)
    paths[missing_key].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


@pytest.mark.parametrize("missing_flag", _flags())
def test_missing_required_flag_failed(tmp_path: Path, missing_flag: str) -> None:
    paths = _prepare(tmp_path)
    flags = [f for f in _flags() if f != missing_flag]
    cp = _run(paths, flags)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


@pytest.mark.parametrize(
    "field",
    [
        "content_item_id",
        "title",
        "volume",
        "author",
        "publisher",
        "release_date",
        "candidate_source_type",
    ],
)
def test_missing_required_candidate_field_failed(tmp_path: Path, field: str) -> None:
    paths = _prepare(tmp_path)
    filled = _read_json(paths["filled"])
    filled[field] = ""
    _write_json(paths["filled"], filled)
    cp = _run(paths)
    assert cp.returncode == 1
    payload = _read_json(paths["result"])
    assert payload["status"] == FAILED


def test_invalid_release_date_format_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    filled = _read_json(paths["filled"])
    filled["release_date"] = "2026/07/06"
    _write_json(paths["filled"], filled)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_ls_new2_fill_status_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    ls2 = _read_json(paths["ls2_result"])
    ls2["status"] = "BAD"
    _write_json(paths["ls2_result"], ls2)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_ls_new2_fill_validation_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["ls2_validation"], {"validation_status": "BAD"})
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_ls_new2_fill_ready_flag_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    ls2 = _read_json(paths["ls2_result"])
    ls2["ready_for_ls_new_3"] = False
    _write_json(paths["ls2_result"], ls2)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_ls_new2_fill_execution_allowed_true_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    ls2 = _read_json(paths["ls2_result"])
    ls2["execution_allowed"] = True
    _write_json(paths["ls2_result"], ls2)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_ls_new2_fill_missing_required_fields_not_empty_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    ls2 = _read_json(paths["ls2_result"])
    ls2["missing_required_human_fields"] = ["title"]
    _write_json(paths["ls2_result"], ls2)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _read_json(paths["result"])["status"] == FAILED


def test_valid_build_passed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    payload = _read_json(paths["result"])
    assert payload["status"] == PASSED


@pytest.mark.parametrize(
    "file_key",
    ["evidence", "inventory", "slots", "xpreview", "wppreview", "result", "lock", "report"],
)
def test_valid_build_creates_expected_files(tmp_path: Path, file_key: str) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    assert paths[file_key].exists()


@pytest.mark.parametrize(
    "key,expected",
    [
        ("phase", "LS-NEW-3"),
        ("execution_mode", "CANDIDATE_EVIDENCE_DRY_RUN_ONLY_NO_EXTERNAL_FETCH"),
        ("production_status", "NO_EXECUTION_CANDIDATE_EVIDENCE_DRY_RUN_ONLY"),
        ("ls_new2_fill_validated", True),
        ("content_item_id", "new-comic-001"),
        ("title", "月曜日のたわわ"),
        ("volume", "第15巻"),
        ("author", "比村奇石"),
        ("publisher", "講談社"),
        ("release_date", "2026-07-06"),
        ("asin", "B0H6DQLPPB"),
        ("isbn", "978-4065442296"),
        ("source_url_inventory_created", True),
        ("store_evidence_slots_created", True),
        ("simple_x_post_preview_created", True),
        ("simple_x_post_under_280", True),
        ("wp_purchase_navigation_preview_created", True),
        ("ready_for_ls_new_4", True),
        ("execution_allowed", False),
        ("external_fetch_executed", False),
        ("http_get_executed", False),
        ("web_scraping_executed", False),
        ("rss_fetch_executed", False),
        ("amazon_api_call_executed", False),
        ("pa_api_call_executed", False),
        ("creators_api_call_executed", False),
        ("x_api_call_executed", False),
        ("x_post_executed", False),
        ("wordpress_api_call_executed", False),
        ("wordpress_write_executed", False),
        ("credential_env_read_executed", False),
        ("credential_value_output", False),
        ("credential_secret_output", False),
        ("secret_length_output", False),
        ("secret_hash_output", False),
        ("candidate_selected", False),
        ("ls_next1_fill_updated", False),
        ("post119_update_executed", False),
        ("post183_update_executed", False),
        ("recommended_next_action", "BEGIN_LS_NEW_4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN"),
    ],
)
def test_result_fields_on_success(tmp_path: Path, key: str, expected) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    payload = _read_json(paths["result"])
    assert payload[key] == expected


def test_result_next_phase_options(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    payload = _read_json(paths["result"])
    assert payload["recommended_next_phase_options"] == ["LS-NEW-4", "LS-MON-2"]


@pytest.mark.parametrize(
    "field,present_expected",
    [
        ("publisher_source_url", True),
        ("kindle_url", True),
        ("rakuten_kobo_url", True),
        ("dmm_books_url", True),
        ("ebookjapan_url", False),
        ("booklive_url", False),
        ("manual_source_url", False),
    ],
)
def test_source_inventory_present_flags(tmp_path: Path, field: str, present_expected: bool) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    inv = _read_json(paths["inventory"])
    assert inv[field]["present"] is present_expected


@pytest.mark.parametrize(
    "field,status_expected",
    [
        ("publisher_source_url", "DRY_RUN_NOT_FETCHED"),
        ("kindle_url", "DRY_RUN_NOT_FETCHED"),
        ("rakuten_kobo_url", "DRY_RUN_NOT_FETCHED"),
        ("dmm_books_url", "DRY_RUN_NOT_FETCHED"),
        ("ebookjapan_url", "NOT_PROVIDED"),
        ("booklive_url", "NOT_PROVIDED"),
        ("manual_source_url", "NOT_PROVIDED"),
    ],
)
def test_source_inventory_statuses(tmp_path: Path, field: str, status_expected: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    inv = _read_json(paths["inventory"])
    assert inv[field]["verification_status"] == status_expected
    assert inv[field]["fetch_executed"] is False


@pytest.mark.parametrize(
    "store,url_present_expected,status_expected",
    [
        ("publisher_official", True, "DRY_RUN_NOT_FETCHED"),
        ("kindle", True, "DRY_RUN_NOT_FETCHED"),
        ("rakuten_kobo", True, "DRY_RUN_NOT_FETCHED"),
        ("dmm_books", True, "DRY_RUN_NOT_FETCHED"),
        ("ebookjapan", False, "NOT_PROVIDED"),
        ("booklive", False, "NOT_PROVIDED"),
        ("manual_source", False, "NOT_PROVIDED"),
    ],
)
def test_store_slots(tmp_path: Path, store: str, url_present_expected: bool, status_expected: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    slots = _read_json(paths["slots"])["slots"]
    slot = {s["store"]: s for s in slots}[store]
    assert slot["url_present"] is url_present_expected
    assert slot["verification_status"] == status_expected
    assert slot["fetch_executed"] is False
    assert slot["api_call_executed"] is False


@pytest.mark.parametrize(
    "key,expected",
    [
        ("generated", True),
        ("x_post_executed", False),
        ("under_280", True),
        ("contains_pr", True),
        ("contains_title", True),
        ("contains_author_hashtag", True),
        ("contains_url_placeholder", True),
    ],
)
def test_x_preview_fields(tmp_path: Path, key: str, expected) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    x_preview = _read_json(paths["xpreview"])
    assert x_preview[key] == expected


def test_x_preview_contains_required_texts(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    x_preview = _read_json(paths["xpreview"])
    text = x_preview["post_text"]
    assert "#PR" in text
    assert "#Amazonmanga" in text
    assert "#Kindle" in text
    assert "#比村奇石" in text
    assert "月曜日のたわわ" in text
    assert "URL" in text


def test_wp_preview_contains_required_texts(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    text = paths["wppreview"].read_text(encoding="utf-8")
    assert "月曜日のたわわ" in text
    assert "第15巻" in text
    assert "2026-07-06" in text
    assert "このプレビューは人間入力値のみを元にしたDRY_RUNです。" in text
    assert "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。" in text


def test_evidence_record_has_expected_sections(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    evidence = _read_json(paths["evidence"])
    for k in [
        "candidate_identity",
        "release_evidence",
        "identifier_evidence",
        "source_url_inventory",
        "store_evidence_slots",
        "simple_x_post_preview",
        "wordpress_purchase_navigation_preview",
        "safety",
    ]:
        assert k in evidence


@pytest.mark.parametrize(
    "safety_key",
    [
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "execution_allowed",
    ],
)
def test_evidence_safety_flags_false(tmp_path: Path, safety_key: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    evidence = _read_json(paths["evidence"])
    assert evidence["safety"][safety_key] is False


@pytest.mark.parametrize(
    "pattern",
    [
        "requests.",
        "urllib.request",
        "wp-json",
        "http.client",
        "Authorization:",
        "base64",
        "b64encode",
    ],
)
def test_source_code_has_no_forbidden_patterns(pattern: str) -> None:
    src = Path(SCRIPT).read_text(encoding="utf-8")
    assert pattern not in src

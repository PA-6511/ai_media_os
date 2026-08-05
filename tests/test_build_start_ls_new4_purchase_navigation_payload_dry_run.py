from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = "scripts/build_start_ls_new4_purchase_navigation_payload_dry_run.py"
PASSED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION"
FAILED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_FAILED_NO_EXECUTION"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _policy() -> dict:
    return {"phase": "LS-NEW-4"}


def _schema() -> dict:
    return {"phase": "LS-NEW-4", "schema_version": "1.0.0"}


def _ls3_result() -> dict:
    return {
        "status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION",
        "ready_for_ls_new_4": True,
        "execution_allowed": False,
        "ls_new2_fill_validated": True,
    }


def _ls3_validation() -> dict:
    return {"validation_status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"}


def _candidate_evidence() -> dict:
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_CANDIDATE_EVIDENCE_DRY_RUN_RECORD",
        "status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_READY_NO_EXECUTION",
        "candidate_identity": {
            "content_item_id": "new-comic-001",
            "title": "月曜日のたわわ",
            "volume": "第15巻",
            "author": "比村奇石",
            "publisher": "講談社",
            "label": "ヤンマガKCスペシャル",
            "release_date": "2026-07-06",
            "ebook_release_date": "2026-07-06",
            "paper_release_date": "2026-07-06",
        },
        "release_evidence": {
            "release_date": "2026-07-06",
            "candidate_source_type": "publisher_official",
            "source_pending": True,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "identifier_evidence": {
            "asin": "B0H6DQLPPB",
            "isbn": "978-4065442296",
            "asin_lookup_executed": False,
            "isbn_lookup_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
    }


def _source_inventory() -> dict:
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_SOURCE_URL_INVENTORY",
        "publisher_source_url": {
            "present": True,
            "url": "https://www.kodansha.co.jp/comic/products/0000428841",
            "fetch_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "kindle_url": {
            "present": True,
            "url": "https://www.amazon.co.jp/dp/406544229X",
            "fetch_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "rakuten_kobo_url": {
            "present": True,
            "url": "https://books.rakuten.co.jp/rk/example",
            "fetch_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "dmm_books_url": {
            "present": True,
            "url": "https://book.dmm.com/product/4071859/latest/",
            "fetch_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "ebookjapan_url": {
            "present": False,
            "url": "",
            "fetch_executed": False,
            "verification_status": "NOT_PROVIDED",
        },
        "booklive_url": {
            "present": False,
            "url": "",
            "fetch_executed": False,
            "verification_status": "NOT_PROVIDED",
        },
        "manual_source_url": {
            "present": False,
            "url": "",
            "fetch_executed": False,
            "verification_status": "NOT_PROVIDED",
        },
    }


def _store_slots() -> dict:
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_STORE_EVIDENCE_SLOTS",
        "slots": [
            {
                "store": "publisher_official",
                "url_present": True,
                "url": "https://www.kodansha.co.jp/comic/products/0000428841",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "DRY_RUN_NOT_FETCHED",
            },
            {
                "store": "kindle",
                "url_present": True,
                "url": "https://www.amazon.co.jp/dp/406544229X",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "DRY_RUN_NOT_FETCHED",
            },
            {
                "store": "rakuten_kobo",
                "url_present": True,
                "url": "https://books.rakuten.co.jp/rk/example",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "DRY_RUN_NOT_FETCHED",
            },
            {
                "store": "dmm_books",
                "url_present": True,
                "url": "https://book.dmm.com/product/4071859/latest/",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "DRY_RUN_NOT_FETCHED",
            },
            {
                "store": "ebookjapan",
                "url_present": False,
                "url": "",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "NOT_PROVIDED",
            },
            {
                "store": "booklive",
                "url_present": False,
                "url": "",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "NOT_PROVIDED",
            },
            {
                "store": "manual_source",
                "url_present": False,
                "url": "",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "NOT_PROVIDED",
            },
        ],
    }


def _x_preview() -> dict:
    post_text = "配信開始です\n#PR #Amazonmanga #Kindle #比村奇石\n『月曜日のたわわ』第15巻\n\nURL"
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_SIMPLE_X_POST_PREVIEW",
        "generated": True,
        "x_post_executed": False,
        "template_source": "LS-NEW-2 simple template",
        "post_text": post_text,
        "character_count": len(post_text),
        "under_280": True,
        "contains_pr": True,
        "contains_title": True,
        "contains_author_hashtag": True,
        "contains_url_placeholder": True,
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "schema": tmp_path / "config/schema.json",
        "ls3_result": tmp_path / "exchange/runtime/ls3_result.json",
        "ls3_validation": tmp_path / "exchange/logs/ls3_validation.json",
        "candidate": tmp_path / "exchange/new_release/candidate.json",
        "source_inventory": tmp_path / "exchange/new_release/source_inventory.json",
        "store_slots": tmp_path / "exchange/new_release/store_slots.json",
        "x_preview": tmp_path / "exchange/new_release/x_preview.json",
        "wp_preview": tmp_path / "exchange/new_release/wp_preview.md",
        "wp_payload": tmp_path / "exchange/new_release/wp_payload.json",
        "wp_preview_out": tmp_path / "exchange/new_release/wp_preview_out.md",
        "x_payload": tmp_path / "exchange/new_release/x_payload.json",
        "validation_summary": tmp_path / "exchange/new_release/validation_summary.json",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "report": tmp_path / "reports/report.md",
    }
    _write_json(paths["policy"], _policy())
    _write_json(paths["schema"], _schema())
    _write_json(paths["ls3_result"], _ls3_result())
    _write_json(paths["ls3_validation"], _ls3_validation())
    _write_json(paths["candidate"], _candidate_evidence())
    _write_json(paths["source_inventory"], _source_inventory())
    _write_json(paths["store_slots"], _store_slots())
    _write_json(paths["x_preview"], _x_preview())
    paths["wp_preview"].parent.mkdir(parents=True, exist_ok=True)
    paths["wp_preview"].write_text(
        "# LS-NEW-3 WordPress Purchase Navigation Preview\n\n- Phase: LS-NEW-3\n- Execution: NO_EXECUTION / PREVIEW_ONLY\n- WordPress write executed: false\n\n## Candidate\n\n- Title: 月曜日のたわわ\n- Volume: 第15巻\n- Author: 比村奇石\n- Publisher: 講談社\n- Release date: 2026-07-06\n- ASIN: B0H6DQLPPB\n- ISBN: 978-4065442296\n\n## Purchase Navigation Draft Preview\n\n【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補\n\n配信・販売ストア候補:\n- 出版社公式: URL入力あり / 未取得\n- Kindle: URL入力あり / 未取得\n- 楽天Kobo: URL入力あり / 未取得\n- DMMブックス: URL入力あり / 未取得\n- ebookjapan: URL未入力\n- BookLive: URL未入力\n\n確認状態:\nこのプレビューは人間入力値のみを元にしたDRY_RUNです。\n外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。\n",
        encoding="utf-8",
    )
    return paths


def _flags() -> list[str]:
    return [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
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
        "--ls-new3-result",
        str(paths["ls3_result"]),
        "--ls-new3-validation-result",
        str(paths["ls3_validation"]),
        "--candidate-evidence-record",
        str(paths["candidate"]),
        "--source-inventory",
        str(paths["source_inventory"]),
        "--store-slots",
        str(paths["store_slots"]),
        "--x-preview",
        str(paths["x_preview"]),
        "--wp-preview",
        str(paths["wp_preview"]),
        "--output-wp-payload",
        str(paths["wp_payload"]),
        "--output-wp-preview",
        str(paths["wp_preview_out"]),
        "--output-x-payload",
        str(paths["x_payload"]),
        "--output-validation-summary",
        str(paths["validation_summary"]),
        "--output",
        str(paths["result"]),
        "--lock-output",
        str(paths["lock"]),
        "--report",
        str(paths["report"]),
    ] + flags
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _result(paths: dict[str, Path]) -> dict:
    return _read_json(paths["result"])


@pytest.mark.parametrize("missing_key", ["policy", "schema", "ls3_result", "ls3_validation", "candidate", "source_inventory", "store_slots", "x_preview", "wp_preview"])
def test_missing_required_input_failed(tmp_path: Path, missing_key: str) -> None:
    paths = _prepare(tmp_path)
    paths[missing_key].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _result(paths)["status"] == FAILED


@pytest.mark.parametrize("missing_flag", _flags())
def test_missing_required_flag_failed(tmp_path: Path, missing_flag: str) -> None:
    paths = _prepare(tmp_path)
    flags = [flag for flag in _flags() if flag != missing_flag]
    cp = _run(paths, flags)
    assert cp.returncode == 1
    assert _result(paths)["status"] == FAILED


@pytest.mark.parametrize("field", ["content_item_id", "title", "volume", "author", "publisher", "release_date"])
def test_missing_required_candidate_field_failed(tmp_path: Path, field: str) -> None:
    paths = _prepare(tmp_path)
    candidate = _read_json(paths["candidate"])
    candidate["candidate_identity"][field] = ""
    _write_json(paths["candidate"], candidate)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _result(paths)["status"] == FAILED


def test_invalid_release_date_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    candidate = _read_json(paths["candidate"])
    candidate["candidate_identity"]["release_date"] = "2026/07/06"
    _write_json(paths["candidate"], candidate)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _result(paths)["status"] == FAILED


def test_valid_build_passed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    assert _result(paths)["status"] == PASSED


@pytest.mark.parametrize("output_key", ["wp_payload", "wp_preview_out", "x_payload", "validation_summary", "result", "lock", "report"])
def test_valid_build_creates_outputs(tmp_path: Path, output_key: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert paths[output_key].exists()


@pytest.mark.parametrize(
    "key,expected",
    [
        ("ls_new3_validated", True),
        ("content_item_id", "new-comic-001"),
        ("title", "月曜日のたわわ"),
        ("volume", "第15巻"),
        ("author", "比村奇石"),
        ("publisher", "講談社"),
        ("release_date", "2026-07-06"),
        ("asin", "B0H6DQLPPB"),
        ("isbn", "978-4065442296"),
        ("wp_payload_created", True),
        ("wp_preview_created", True),
        ("x_payload_created", True),
        ("payload_validation_summary_created", True),
        ("purchase_navigation_media", True),
        ("work_explanation_media", False),
        ("simple_x_post_under_280", True),
        ("ready_for_ls_new_5_human_review", True),
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
        ("recommended_next_action", "BEGIN_LS_NEW_5_HUMAN_REVIEW_GATE"),
    ],
)
def test_result_fields_on_success(tmp_path: Path, key: str, expected) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _result(paths)[key] == expected


def test_result_next_phase_options(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _result(paths)["recommended_next_phase_options"] == ["LS-NEW-5", "LS-MON-2"]


@pytest.mark.parametrize("field,present_expected", [("publisher_source_url", True), ("kindle_url", True), ("rakuten_kobo_url", True), ("dmm_books_url", True), ("ebookjapan_url", False), ("booklive_url", False), ("manual_source_url", False)])
def test_source_inventory_presence(tmp_path: Path, field: str, present_expected: bool) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    inv = _read_json(paths["source_inventory"])
    assert inv[field]["present"] is present_expected


@pytest.mark.parametrize("field,status_expected", [("publisher_source_url", "DRY_RUN_NOT_FETCHED"), ("kindle_url", "DRY_RUN_NOT_FETCHED"), ("rakuten_kobo_url", "DRY_RUN_NOT_FETCHED"), ("dmm_books_url", "DRY_RUN_NOT_FETCHED"), ("ebookjapan_url", "NOT_PROVIDED"), ("booklive_url", "NOT_PROVIDED"), ("manual_source_url", "NOT_PROVIDED")])
def test_source_inventory_statuses(tmp_path: Path, field: str, status_expected: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    inv = _read_json(paths["source_inventory"])
    assert inv[field]["verification_status"] == status_expected
    assert inv[field]["fetch_executed"] is False


@pytest.mark.parametrize("store,url_present_expected,status_expected", [("publisher_official", True, "DRY_RUN_NOT_FETCHED"), ("kindle", True, "DRY_RUN_NOT_FETCHED"), ("rakuten_kobo", True, "DRY_RUN_NOT_FETCHED"), ("dmm_books", True, "DRY_RUN_NOT_FETCHED"), ("ebookjapan", False, "NOT_PROVIDED"), ("booklive", False, "NOT_PROVIDED"), ("manual_source", False, "NOT_PROVIDED")])
def test_store_slots(tmp_path: Path, store: str, url_present_expected: bool, status_expected: str) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    slots = {slot["store"]: slot for slot in _read_json(paths["store_slots"])["slots"]}
    slot = slots[store]
    assert slot["url_present"] is url_present_expected
    assert slot["verification_status"] == status_expected
    assert slot["fetch_executed"] is False
    assert slot["api_call_executed"] is False


@pytest.mark.parametrize("key,expected", [("generated", True), ("x_post_executed", False), ("under_280", True), ("contains_pr", True), ("contains_title", True), ("contains_author_hashtag", True), ("contains_url_placeholder", True)])
def test_x_payload_flags(tmp_path: Path, key: str, expected) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _read_json(paths["x_payload"])[key] == expected


def test_x_payload_text_contains_required_content(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    text = _read_json(paths["x_payload"])["post_text"]
    assert "#PR" in text
    assert "#Amazonmanga" in text
    assert "#Kindle" in text
    assert "#比村奇石" in text
    assert "月曜日のたわわ" in text
    assert "URL" in text


@pytest.mark.parametrize("key,expected", [("wp_payload_valid", True), ("x_payload_valid", True), ("purchase_navigation_media", True), ("work_explanation_media", False), ("official_synopsis_copy_included", False), ("store_description_copy_included", False), ("review_copy_included", False), ("x_post_under_280", True), ("external_fetch_executed", False), ("wordpress_write_executed", False), ("x_post_executed", False), ("ready_for_ls_new_5_human_review", True), ("execution_allowed", False)])
def test_validation_summary_flags(tmp_path: Path, key: str, expected) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    assert _read_json(paths["validation_summary"])[key] == expected


def test_wp_payload_body_and_disclosure(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _run(paths)
    wp = _read_json(paths["wp_payload"])
    body = wp["body_markdown"]
    assert wp["post_title"] == "【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補"
    assert "このページにはPR・アフィリエイトリンクを含む場合があります。" in wp["affiliate_disclosure"]
    assert "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。" in wp["external_fetch_notice"]
    assert "## 基本情報" in body
    assert "## 販売ストア候補" in body
    assert "## 確認状態" in body
    assert "## PR表記" in body
    assert "月曜日のたわわ" in body
    assert "第15巻" in body
    assert "2026-07-06" in body
    assert "このページにはPR・アフィリエイトリンクを含む場合があります。" in body
    assert "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。" in body
    assert "あらすじ" not in body
    assert "レビュー" not in body


@pytest.mark.parametrize("pattern", ["requests.", "urllib.request", "wp-json", "/wp/v2/posts", "credential.env", "Authorization:", "base64", "b64encode"])
def test_source_code_has_no_forbidden_patterns(pattern: str) -> None:
    src = Path(SCRIPT).read_text(encoding="utf-8")
    assert pattern not in src

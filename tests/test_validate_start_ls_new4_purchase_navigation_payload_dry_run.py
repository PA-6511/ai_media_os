from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


BUILD_SCRIPT = "scripts/build_start_ls_new4_purchase_navigation_payload_dry_run.py"
VALIDATE_SCRIPT = "scripts/validate_start_ls_new4_purchase_navigation_payload_dry_run.py"
VALIDATED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_NOT_VALIDATED"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_policy() -> dict:
    return {"phase": "LS-NEW-4"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-4", "schema_version": "1.0.0"}


def _base_ls3_result() -> dict:
    return {
        "status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION",
        "ready_for_ls_new_4": True,
        "execution_allowed": False,
        "ls_new2_fill_validated": True,
    }


def _base_ls3_validation() -> dict:
    return {"validation_status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"}


def _base_candidate_evidence() -> dict:
    return {
        "phase": "LS-NEW-3",
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
        "identifier_evidence": {"asin": "B0H6DQLPPB", "isbn": "978-4065442296"},
    }


def _base_source_inventory() -> dict:
    return {
        "phase": "LS-NEW-3",
        "publisher_source_url": {"present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False},
        "kindle_url": {"present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False},
        "rakuten_kobo_url": {"present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False},
        "dmm_books_url": {"present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False},
        "ebookjapan_url": {"present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False},
        "booklive_url": {"present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False},
        "manual_source_url": {"present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False},
    }


def _base_store_slots() -> dict:
    return {
        "phase": "LS-NEW-3",
        "slots": [
            {"store": "publisher_official", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False, "api_call_executed": False},
            {"store": "kindle", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False, "api_call_executed": False},
            {"store": "rakuten_kobo", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False, "api_call_executed": False},
            {"store": "dmm_books", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED", "fetch_executed": False, "api_call_executed": False},
            {"store": "ebookjapan", "url_present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False, "api_call_executed": False},
            {"store": "booklive", "url_present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False, "api_call_executed": False},
            {"store": "manual_source", "url_present": False, "verification_status": "NOT_PROVIDED", "fetch_executed": False, "api_call_executed": False},
        ],
    }


def _base_x_payload() -> dict:
    post_text = "配信開始です\n#PR #Amazonmanga #Kindle #比村奇石\n『月曜日のたわわ』第15巻\n\nURL"
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_X_POST_PAYLOAD_DRY_RUN",
        "generated": True,
        "x_post_executed": False,
        "x_api_call_executed": False,
        "template_source": "LS-NEW-3 simple X preview",
        "post_text": post_text,
        "character_count": len(post_text),
        "under_280": True,
        "contains_pr": True,
        "contains_title": True,
        "contains_author_hashtag": True,
        "contains_url_placeholder": True,
        "content_policy": {
            "synopsis_included": False,
            "price_comparison_required": False,
            "point_reward_rate_required": False,
            "store_comparison_required": False,
            "long_work_explanation_included": False,
        },
        "safety": {"x_post_executed": False, "x_api_call_executed": False, "execution_allowed": False},
    }


def _base_wp_payload() -> dict:
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_WP_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN",
        "generated": True,
        "wordpress_write_executed": False,
        "wordpress_api_call_executed": False,
        "post_status_target": "draft",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "candidate_identity": {
            "content_item_id": "new-comic-001",
            "title": "月曜日のたわわ",
            "volume": "第15巻",
            "author": "比村奇石",
            "publisher": "講談社",
            "release_date": "2026-07-06",
            "asin": "B0H6DQLPPB",
            "isbn": "978-4065442296",
        },
        "post_title": "【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補",
        "body_markdown": "# 【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補\n\nこのページは、新刊コミック『月曜日のたわわ』第15巻の発売日・販売ストア候補を整理する購入ナビ用DRY_RUNです。\n\n## 基本情報\n\n- 作品名: 月曜日のたわわ\n- 巻数: 第15巻\n- 作者: 比村奇石\n- 出版社: 講談社\n- 発売日: 2026-07-06\n- ASIN: B0H6DQLPPB\n- ISBN: 978-4065442296\n\n## 販売ストア候補\n\n- 出版社公式: URL入力あり / 未取得\n- Kindle: URL入力あり / 未取得\n- 楽天Kobo: URL入力あり / 未取得\n- DMMブックス: URL入力あり / 未取得\n- ebookjapan: URL未入力\n- BookLive: URL未入力\n\n## 確認状態\n\nこのpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。\n外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。\n\n## PR表記\n\nこのページにはPR・アフィリエイトリンクを含む場合があります。\n",
        "affiliate_disclosure": "このページにはPR・アフィリエイトリンクを含む場合があります。",
        "external_fetch_notice": "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。",
        "store_candidate_list": [
            {"store": "出版社公式", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED"},
            {"store": "Kindle", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED"},
            {"store": "楽天Kobo", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED"},
            {"store": "DMMブックス", "url_present": True, "verification_status": "DRY_RUN_NOT_FETCHED"},
            {"store": "ebookjapan", "url_present": False, "verification_status": "NOT_PROVIDED"},
            {"store": "BookLive", "url_present": False, "verification_status": "NOT_PROVIDED"},
        ],
        "content_policy": {
            "work_explanation_required": False,
            "long_work_explanation_required": False,
            "synopsis_required": False,
            "official_synopsis_copy_included": False,
            "store_description_copy_included": False,
            "publisher_description_copy_included": False,
            "review_copy_included": False,
        },
        "safety": {"external_fetch_executed": False, "http_get_executed": False, "wordpress_api_call_executed": False, "wordpress_write_executed": False, "execution_allowed": False},
    }


def _base_validation_summary() -> dict:
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PAYLOAD_VALIDATION_SUMMARY",
        "wp_payload_valid": True,
        "x_payload_valid": True,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "official_synopsis_copy_included": False,
        "store_description_copy_included": False,
        "review_copy_included": False,
        "x_post_under_280": True,
        "external_fetch_executed": False,
        "wordpress_write_executed": False,
        "x_post_executed": False,
        "ready_for_ls_new_5_human_review": True,
        "execution_allowed": False,
        "errors": [],
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "schema": tmp_path / "config/schema.json",
        "ls3_result": tmp_path / "exchange/runtime/ls3_result.json",
        "ls3_validation": tmp_path / "exchange/logs/ls3_validation.json",
        "wp_payload": tmp_path / "exchange/new_release/wp_payload.json",
        "wp_preview": tmp_path / "exchange/new_release/wp_preview.md",
        "x_payload": tmp_path / "exchange/new_release/x_payload.json",
        "validation_summary": tmp_path / "exchange/new_release/validation_summary.json",
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/report.md",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["schema"], _base_schema())
    _write_json(paths["ls3_result"], _base_ls3_result())
    _write_json(paths["ls3_validation"], _base_ls3_validation())
    _write_json(paths["wp_payload"], _base_wp_payload())
    paths["wp_preview"].parent.mkdir(parents=True, exist_ok=True)
    paths["wp_preview"].write_text(
        "# LS-NEW-4 WordPress Purchase Navigation Preview\n\n"
        "- Phase: LS-NEW-4\n"
        "- Execution: NO_EXECUTION / PREVIEW_ONLY\n"
        "- WordPress write executed: false\n\n"
        "## Candidate\n\n"
        "- Title: 月曜日のたわわ\n"
        "- Volume: 第15巻\n"
        "- Author: 比村奇石\n"
        "- Publisher: 講談社\n"
        "- Release date: 2026-07-06\n"
        "- ASIN: B0H6DQLPPB\n"
        "- ISBN: 978-4065442296\n\n"
        "## Purchase Navigation Draft Preview\n\n"
        "【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補\n\n"
        "配信・販売ストア候補:\n"
        "- 出版社公式: URL入力あり / 未取得\n"
        "- Kindle: URL入力あり / 未取得\n"
        "- 楽天Kobo: URL入力あり / 未取得\n"
        "- DMMブックス: URL入力あり / 未取得\n"
        "- ebookjapan: URL未入力\n"
        "- BookLive: URL未入力\n\n"
        "確認状態:\n"
        "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。\n"
        "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。\n\n"
        "## PR表記\n\n"
        "このページにはPR・アフィリエイトリンクを含む場合があります。\n",
        encoding="utf-8",
    )
    _write_json(paths["x_payload"], _base_x_payload())
    _write_json(paths["validation_summary"], _base_validation_summary())
    _write_json(paths["result"], {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_RESULT",
        "status": "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION",
        "execution_mode": "PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_ONLY_NO_EXTERNAL_FETCH",
        "production_status": "NO_EXECUTION_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_ONLY",
        "ls_new3_validated": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "asin": "B0H6DQLPPB",
        "isbn": "978-4065442296",
        "wp_payload_created": True,
        "wp_preview_created": True,
        "x_payload_created": True,
        "payload_validation_summary_created": True,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "simple_x_post_under_280": True,
        "ready_for_ls_new_5_human_review": True,
        "execution_allowed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    })
    _write_json(paths["run_result"], _read_json(paths["result"]))
    _write_json(paths["lock"], {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_LOCK",
        "status": "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_LOCKED_NO_EXECUTION",
        "locked": True,
        "ready_for_ls_new_5_human_review": True,
        "execution_allowed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    })
    return paths


def _run_validate(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        VALIDATE_SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--schema",
        str(paths["schema"]),
        "--wp-payload",
        str(paths["wp_payload"]),
        "--wp-preview",
        str(paths["wp_preview"]),
        "--x-payload",
        str(paths["x_payload"]),
        "--validation-summary",
        str(paths["validation_summary"]),
        "--result",
        str(paths["result"]),
        "--lock",
        str(paths["lock"]),
        "--run-result",
        str(paths["run_result"]),
        "--ls-new3-validation-result",
        str(paths["ls3_validation"]),
        "--output",
        str(paths["output"]),
        "--report",
        str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


@pytest.mark.parametrize("missing_key", ["wp_payload", "wp_preview", "x_payload", "validation_summary", "result", "lock", "run_result"])
def test_validation_detects_missing_inputs(tmp_path: Path, missing_key: str) -> None:
    paths = _prepare(tmp_path)
    paths[missing_key].unlink()
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


def test_validation_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run_validate(paths)
    assert cp.returncode == 0
    assert _read_json(paths["output"])["validation_status"] == VALIDATED


@pytest.mark.parametrize("key", ["status", "production_status"])
def test_validation_detects_result_mismatch(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    result = _read_json(paths["result"])
    result[key] = "BAD"
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize(
    "key",
    [
        "ready_for_ls_new_5_human_review",
        "execution_allowed",
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
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_validation_detects_result_forbidden_true(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    result = _read_json(paths["result"])
    result[key] = not bool(result.get(key, False))
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_wp_payload_missing_pr_disclosure(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    wp = _read_json(paths["wp_payload"])
    wp["affiliate_disclosure"] = ""
    _write_json(paths["wp_payload"], wp)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_wp_payload_missing_external_notice(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    wp = _read_json(paths["wp_payload"])
    wp["external_fetch_notice"] = ""
    _write_json(paths["wp_payload"], wp)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_x_payload_over_280(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    x_payload = _read_json(paths["x_payload"])
    x_payload["post_text"] = "A" * 281
    x_payload["character_count"] = 281
    x_payload["under_280"] = False
    _write_json(paths["x_payload"], x_payload)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize(
    "mutate",
    [
        lambda x: x.update({"post_text": x["post_text"].replace("#PR", "")}),
        lambda x: x.update({"post_text": x["post_text"].replace("URL", "")}),
        lambda x: x.update({"post_text": x["post_text"].replace("#比村奇石", "")}),
    ],
)
def test_validation_detects_x_payload_text_issues(tmp_path: Path, mutate) -> None:
    paths = _prepare(tmp_path)
    x_payload = _read_json(paths["x_payload"])
    mutate(x_payload)
    _write_json(paths["x_payload"], x_payload)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize("key", ["wp_payload_valid", "x_payload_valid", "purchase_navigation_media", "work_explanation_media", "official_synopsis_copy_included", "store_description_copy_included", "review_copy_included", "x_post_under_280", "external_fetch_executed", "wordpress_write_executed", "x_post_executed", "ready_for_ls_new_5_human_review", "execution_allowed"])
def test_validation_summary_mismatch(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    summary = _read_json(paths["validation_summary"])
    summary[key] = not summary[key] if isinstance(summary[key], bool) else False
    _write_json(paths["validation_summary"], summary)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize("key", ["status", "ready_for_ls_new_5_human_review", "execution_allowed"])
def test_validation_detects_lock_mismatch(tmp_path: Path, key: str) -> None:
    paths = _prepare(tmp_path)
    lock = _read_json(paths["lock"])
    if key == "status":
        lock[key] = "BAD"
    else:
        lock[key] = not lock[key] if isinstance(lock[key], bool) else lock[key]
    _write_json(paths["lock"], lock)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize("pattern", ["requests.", "urllib.request", "wp-json", "/wp/v2/posts", "credential.env", "Authorization:", "base64"])
def test_source_code_has_no_forbidden_patterns(pattern: str) -> None:
    src = Path(BUILD_SCRIPT).read_text(encoding="utf-8") + Path(VALIDATE_SCRIPT).read_text(encoding="utf-8")
    assert pattern not in src

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


BUILD_SCRIPT = "scripts/build_start_ls_new3_candidate_evidence_dry_run.py"
VALIDATE_SCRIPT = "scripts/validate_start_ls_new3_candidate_evidence_dry_run.py"
VALIDATED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_NOT_VALIDATED"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_flags() -> list[str]:
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
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "validation_output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/report.md",
        "build_report": tmp_path / "reports/build_report.md",
    }

    _write_json(paths["policy"], {"phase": "LS-NEW-3"})
    _write_json(paths["schema"], {"phase": "LS-NEW-3", "schema_version": "1.0.0"})
    _write_json(
        paths["ls2_result"],
        {
            "status": "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION",
            "ready_for_ls_new_3": True,
            "execution_allowed": False,
            "missing_required_human_fields": [],
        },
    )
    _write_json(
        paths["ls2_validation"],
        {"validation_status": "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"},
    )
    _write_json(
        paths["filled"],
        {
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
        },
    )

    build_cmd = [
        sys.executable,
        BUILD_SCRIPT,
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
        str(paths["build_report"]),
    ] + _build_flags()
    cp = subprocess.run(build_cmd, text=True, capture_output=True, check=False)
    assert cp.returncode == 0
    _write_json(paths["run_result"], _read_json(paths["result"]))
    return paths


def _run_validate(paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        VALIDATE_SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--schema",
        str(paths["schema"]),
        "--evidence-record",
        str(paths["evidence"]),
        "--source-inventory",
        str(paths["inventory"]),
        "--store-slots",
        str(paths["slots"]),
        "--x-preview",
        str(paths["xpreview"]),
        "--wp-preview",
        str(paths["wppreview"]),
        "--result",
        str(paths["result"]),
        "--lock",
        str(paths["lock"]),
        "--run-result",
        str(paths["run_result"]),
        "--ls-new2-fill-validation-result",
        str(paths["ls2_validation"]),
        "--output",
        str(paths["validation_output"]),
        "--report",
        str(paths["report"]),
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_validation_valid(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    cp = _run_validate(paths)
    assert cp.returncode == 0
    assert _read_json(paths["validation_output"])["validation_status"] == VALIDATED


@pytest.mark.parametrize(
    "missing_key",
    [
        "evidence",
        "inventory",
        "slots",
        "xpreview",
        "wppreview",
        "result",
        "lock",
        "run_result",
    ],
)
def test_validation_detects_missing_inputs(tmp_path: Path, missing_key: str) -> None:
    paths = _prepare(tmp_path)
    paths[missing_key].unlink()
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    result = _read_json(paths["result"])
    result["status"] = "BAD"
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_production_status_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    result = _read_json(paths["result"])
    result["production_status"] = "BAD"
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize(
    "key",
    [
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
    result[key] = True
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_ready_for_ls_new_4_false(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    result = _read_json(paths["result"])
    result["ready_for_ls_new_4"] = False
    _write_json(paths["result"], result)
    _write_json(paths["run_result"], result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize(
    "mutate",
    [
        lambda x: x.update({"under_280": False}),
        lambda x: x.update({"post_text": "A" * 281}),
        lambda x: x.update({"post_text": x["post_text"].replace("#PR", "")}),
        lambda x: x.update({"post_text": x["post_text"].replace("URL", "")}),
        lambda x: x.update({"contains_pr": False}),
        lambda x: x.update({"contains_url_placeholder": False}),
    ],
)
def test_validation_detects_x_preview_errors(tmp_path: Path, mutate) -> None:
    paths = _prepare(tmp_path)
    x_preview = _read_json(paths["xpreview"])
    mutate(x_preview)
    _write_json(paths["xpreview"], x_preview)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_store_slot_fetch_executed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    slots = _read_json(paths["slots"])
    slots["slots"][0]["fetch_executed"] = True
    _write_json(paths["slots"], slots)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_store_slot_api_call_executed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    slots = _read_json(paths["slots"])
    slots["slots"][0]["api_call_executed"] = True
    _write_json(paths["slots"], slots)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_source_inventory_fetch_executed_true(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    inv = _read_json(paths["inventory"])
    inv["kindle_url"]["fetch_executed"] = True
    _write_json(paths["inventory"], inv)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_wp_preview_statement_missing(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    text = paths["wppreview"].read_text(encoding="utf-8").replace("外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。", "")
    paths["wppreview"].write_text(text, encoding="utf-8")
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_result_and_run_result_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    run_result = _read_json(paths["run_result"])
    run_result["status"] = "OTHER"
    _write_json(paths["run_result"], run_result)
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


def test_validation_detects_ls_new2_validation_mismatch(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["ls2_validation"], {"validation_status": "BAD"})
    cp = _run_validate(paths)
    assert cp.returncode == 1
    assert _read_json(paths["validation_output"])["validation_status"] == NOT_VALIDATED


@pytest.mark.parametrize(
    "pattern",
    [
        "requests.",
        "urllib.request",
        "wp-json",
        "/wp/v2/posts",
        "credential.env",
        "Authorization:",
        "base64",
    ],
)
def test_source_code_has_no_forbidden_patterns(pattern: str) -> None:
    src = Path(BUILD_SCRIPT).read_text(encoding="utf-8") + Path(VALIDATE_SCRIPT).read_text(encoding="utf-8")
    assert pattern not in src

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/build_start_ls_new2_fill_human_new_release_comic_candidate.py"
WAITING = "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_NO_EXECUTION"
PASSED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION"
FAILED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_FAILED_NO_EXECUTION"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-2-FILL",
        "required_previous_phase": {
            "required_ls_new2_status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
            "required_ls_new2_validation_status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
            "required_ls_new2_production_status": "NO_EXECUTION_NEW_RELEASE_CANDIDATE_INTAKE_ONLY",
            "required_simple_x_template_under_280": True,
            "required_ready_for_ls_new_3": False,
            "required_execution_allowed": False,
        },
        "next_phase": {
            "recommended_next_action_waiting": "WAIT_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT",
            "recommended_next_action_valid": "BEGIN_LS_NEW_3_CANDIDATE_EVIDENCE_DRY_RUN",
            "recommended_next_phase_options_waiting": ["LS-NEW-2-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"],
            "recommended_next_phase_options_valid": ["LS-NEW-3_AFTER_HUMAN_INPUT", "LS-MON-2"],
        },
    }


def _base_ls_new2_result() -> dict:
    return {
        "status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEW_RELEASE_CANDIDATE_INTAKE_ONLY",
        "simple_x_template_under_280": True,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
    }


def _base_ls_new2_lock() -> dict:
    return {"locked": True}


def _base_ls_new2_validation() -> dict:
    return {
        "validation_status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
    }


def _base_ls_new2_schema() -> dict:
    return {"phase": "LS-NEW-2"}


def _base_ls_new2_template() -> dict:
    return {"document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_TEMPLATE"}


def _base_ls_new2_record() -> dict:
    return {"document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RECORD"}


def _base_human_input_record() -> dict:
    return {
        "document_type": "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_RECORD",
        "phase": "LS-NEW-2-FILL",
        "status": "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": "",
        "title": "",
        "volume": "",
        "author": "",
        "publisher": "",
        "release_date": "",
        "candidate_source_type": "",
        "publisher_source_url": "",
        "kindle_url": "",
        "rakuten_kobo_url": "",
        "dmm_books_url": "",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "simple_x_post_template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
        "simple_x_post_max_characters": 280,
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
    }


def _base_simple_x_md() -> str:
    return """# START-LS LS-NEW-2 Simple X Post Template

```text
配信開始です
#PR #Amazonmanga #Kindle #作者名
『タイトル』第○巻

URL
```
"""


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "ls2_result": tmp_path / "exchange/runtime/ls2_result.json",
        "ls2_lock": tmp_path / "exchange/locks/ls2_lock.json",
        "ls2_run_result": tmp_path / "exchange/logs/ls2_run_result.json",
        "ls2_validation": tmp_path / "exchange/logs/ls2_validation.json",
        "ls2_schema": tmp_path / "config/ls2_schema.json",
        "ls2_template": tmp_path / "exchange/new_release/ls2_template.json",
        "ls2_record": tmp_path / "exchange/new_release/ls2_record.json",
        "simple_x": tmp_path / "exchange/templates/simple_x.md",
        "human_input_template": tmp_path / "exchange/new_release/human_input_template.json",
        "human_input_record": tmp_path / "exchange/new_release/human_input_record.json",
        "filled_output": tmp_path / "exchange/new_release/filled_candidate.json",
        "result_out": tmp_path / "exchange/runtime/result.json",
        "lock_out": tmp_path / "exchange/locks/lock.json",
        "report_out": tmp_path / "reports/report.md",
    }

    _write_json(paths["policy"], _base_policy())
    ls2_result = _base_ls_new2_result()
    _write_json(paths["ls2_result"], ls2_result)
    _write_json(paths["ls2_run_result"], ls2_result)
    _write_json(paths["ls2_lock"], _base_ls_new2_lock())
    _write_json(paths["ls2_validation"], _base_ls_new2_validation())
    _write_json(paths["ls2_schema"], _base_ls_new2_schema())
    _write_json(paths["ls2_template"], _base_ls_new2_template())
    _write_json(paths["ls2_record"], _base_ls_new2_record())
    paths["simple_x"].parent.mkdir(parents=True, exist_ok=True)
    paths["simple_x"].write_text(_base_simple_x_md(), encoding="utf-8")
    _write_json(paths["human_input_record"], _base_human_input_record())
    return paths


def _flags() -> list[str]:
    return [
        "--create-human-input-template",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-external-fetch",
        "--require-no-amazon-api",
        "--require-no-x-api",
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
        "--ls-new2-result",
        str(paths["ls2_result"]),
        "--ls-new2-lock",
        str(paths["ls2_lock"]),
        "--ls-new2-run-result",
        str(paths["ls2_run_result"]),
        "--ls-new2-validation-result",
        str(paths["ls2_validation"]),
        "--ls-new2-candidate-schema",
        str(paths["ls2_schema"]),
        "--ls-new2-candidate-template",
        str(paths["ls2_template"]),
        "--ls-new2-candidate-record",
        str(paths["ls2_record"]),
        "--ls-new2-simple-x-template",
        str(paths["simple_x"]),
        "--human-input-template-output",
        str(paths["human_input_template"]),
        "--human-input-record",
        str(paths["human_input_record"]),
        "--filled-candidate-output",
        str(paths["filled_output"]),
        "--output",
        str(paths["result_out"]),
        "--lock-output",
        str(paths["lock_out"]),
        "--report",
        str(paths["report_out"]),
    ] + flags
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_missing_flag_failed(tmp_path: Path, missing_flag: str) -> None:
    paths = _prepare(tmp_path)
    flags = [f for f in _flags() if f != missing_flag]
    cp = _run(paths, flags)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def _assert_waiting(tmp_path: Path, mutate=None, flags: list[str] | None = None) -> dict:
    paths = _prepare(tmp_path)
    if mutate:
        rec = _payload(paths["human_input_record"])
        mutate(rec)
        _write_json(paths["human_input_record"], rec)
    cp = _run(paths, flags)
    assert cp.returncode == 0
    payload = _payload(paths["result_out"])
    assert payload["status"] == WAITING
    return payload


def _assert_failed(tmp_path: Path, mutate=None, flags: list[str] | None = None) -> dict:
    paths = _prepare(tmp_path)
    if mutate:
        rec = _payload(paths["human_input_record"])
        mutate(rec)
        _write_json(paths["human_input_record"], rec)
    cp = _run(paths, flags)
    assert cp.returncode == 1
    payload = _payload(paths["result_out"])
    assert payload["status"] == FAILED
    return payload


def _assert_passed(tmp_path: Path) -> dict:
    paths = _prepare(tmp_path)
    rec = _payload(paths["human_input_record"])
    rec.update(
        {
            "content_item_id": "NEW-001",
            "title": "作品名",
            "volume": "第1巻",
            "author": "作者名",
            "publisher": "出版社",
            "release_date": "2026-07-20",
            "candidate_source_type": "manual_confirmation",
            "manual_source_url": "https://example.com/source",
            "source_pending": False,
            "human_filled": True,
            "human_confirmed": True,
        }
    )
    _write_json(paths["human_input_record"], rec)
    cp = _run(paths, _flags() + ["--require-human-filled", "--require-human-confirmed"])
    assert cp.returncode == 0
    payload = _payload(paths["result_out"])
    assert payload["status"] == PASSED
    return payload


# 1-15

def test_01_missing_policy_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_02_missing_lsnew2_result_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls2_result"].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_03_missing_lsnew2_validation_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["ls2_validation"].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_04_lsnew2_status_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    d = _base_ls_new2_result()
    d["status"] = "BAD"
    _write_json(paths["ls2_result"], d)
    _write_json(paths["ls2_run_result"], d)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_05_lsnew2_validation_mismatch_failed(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    _write_json(paths["ls2_validation"], {"validation_status": "BAD"})
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_06_missing_create_human_input_template_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--create-human-input-template")


def test_07_missing_require_no_wordpress_api_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-wordpress-api")


def test_08_missing_require_no_credential_read_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-credential-read")


def test_09_missing_require_no_external_fetch_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-external-fetch")


def test_10_missing_require_no_amazon_api_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-amazon-api")


def test_11_missing_require_no_x_api_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-x-api")


def test_12_missing_require_no_candidate_selection_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-candidate-selection")


def test_13_missing_require_no_ls_next1_fill_update_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-ls-next1-fill-update")


def test_14_missing_forbid_post119_update_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--forbid-post119-update")


def test_15_missing_forbid_post183_update_failed(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--forbid-post183-update")


# 16-29

def test_16_no_human_input_record_waiting(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["human_input_record"].unlink()
    cp = _run(paths)
    assert cp.returncode == 0
    payload = _payload(paths["result_out"])
    assert payload["status"] == WAITING


def test_17_blank_human_input_record_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path)


def test_18_human_filled_false_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"human_filled": False}))


def test_19_human_confirmed_false_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"human_confirmed": False}))


def test_20_missing_content_item_id_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"content_item_id": ""}))


def test_21_missing_title_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"title": ""}))


def test_22_missing_volume_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"volume": ""}))


def test_23_missing_author_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"author": ""}))


def test_24_missing_publisher_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"publisher": ""}))


def test_25_missing_release_date_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"release_date": ""}))


def test_26_missing_candidate_source_type_waiting(tmp_path: Path) -> None:
    _assert_waiting(tmp_path, lambda r: r.update({"candidate_source_type": ""}))


def test_27_no_source_url_and_source_pending_false_failed(tmp_path: Path) -> None:
    _assert_failed(
        tmp_path,
        lambda r: r.update(
            {
                "source_pending": False,
                "publisher_source_url": "",
                "kindle_url": "",
                "rakuten_kobo_url": "",
                "dmm_books_url": "",
                "ebookjapan_url": "",
                "booklive_url": "",
                "manual_source_url": "",
            }
        ),
    )


def test_28_invalid_release_date_format_failed(tmp_path: Path) -> None:
    _assert_failed(tmp_path, lambda r: r.update({"release_date": "2026/07/20"}))


def test_29_valid_human_input_passed(tmp_path: Path) -> None:
    payload = _assert_passed(tmp_path)
    assert payload["status"] == PASSED


# 30-47

def test_30_result_ready_for_ls_new_3_true_when_valid(tmp_path: Path) -> None:
    assert _assert_passed(tmp_path)["ready_for_ls_new_3"] is True


def test_31_result_execution_allowed_false_when_valid(tmp_path: Path) -> None:
    assert _assert_passed(tmp_path)["execution_allowed"] is False


def test_32_result_candidate_intake_completed_true_when_valid(tmp_path: Path) -> None:
    assert _assert_passed(tmp_path)["candidate_intake_completed"] is True


def test_33_result_missing_required_human_fields_empty_when_valid(tmp_path: Path) -> None:
    assert _assert_passed(tmp_path)["missing_required_human_fields"] == []


def test_34_result_simple_x_template_under_280_true(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["simple_x_template_under_280"] is True


def test_35_result_no_wordpress_api(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["wordpress_api_call_executed"] is False


def test_36_result_no_credential_read(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["credential_env_read_executed"] is False


def test_37_result_no_external_api(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["external_api_call_executed"] is False


def test_38_result_no_http_get(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["http_get_executed"] is False


def test_39_result_no_scraping(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["web_scraping_executed"] is False


def test_40_result_no_amazon_api(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["amazon_api_call_executed"] is False


def test_41_result_no_x_api(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["x_api_call_executed"] is False


def test_42_result_no_x_post(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["x_post_executed"] is False


def test_43_result_no_candidate_selected(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["candidate_selected"] is False


def test_44_result_no_ls_next1_fill_update(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["ls_next1_fill_updated"] is False


def test_45_result_no_post119_update(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["post119_update_executed"] is False


def test_46_result_no_post183_update(tmp_path: Path) -> None:
    assert _assert_waiting(tmp_path)["post183_update_executed_by_this_phase"] is False


def test_47_result_no_secret_output(tmp_path: Path) -> None:
    payload = _assert_waiting(tmp_path)
    assert payload["secret_length_output"] is False
    assert payload["secret_hash_output"] is False
    assert payload["authorization_header_output"] is False

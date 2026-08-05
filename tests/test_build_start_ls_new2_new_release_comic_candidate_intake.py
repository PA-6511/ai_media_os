from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/build_start_ls_new2_new_release_comic_candidate_intake.py"
WAITING = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
FAILED = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_FAILED_NO_EXECUTION"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_lsnew1_result() -> dict:
    return {
        "validation_status": "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION",
        "status": "DESIGN_ONLY_NO_EXECUTION",
        "production_status": "NO_GO",
        "sale_route_status": "ON_HOLD",
        "new_release_comic_route_status": "PRIMARY_NEXT_ROUTE",
        "media_type": "purchase_navigation_media",
        "not_media_type": "work_explanation_media",
    }


def _base_lsnew1_policy() -> dict:
    return {"phase": "LS-NEW-1"}


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-2",
        "next_phase": {
            "recommended_next_action": "FILL_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_OR_CONTINUE_MONITORING",
            "recommended_next_phase_options": ["LS-NEW-2-FILL", "LS-MON-2", "LS-NEW-3_AFTER_HUMAN_INPUT"],
        },
        "required_previous_phase": {
            "ls_new1": {
                "required_validation_status": "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION",
                "required_status": "DESIGN_ONLY_NO_EXECUTION",
                "required_production_status": "NO_GO",
                "required_sale_route_status": "ON_HOLD",
                "required_new_release_comic_route_status": "PRIMARY_NEXT_ROUTE",
                "required_media_type": "purchase_navigation_media",
                "required_not_media_type": "work_explanation_media",
            }
        },
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "lsnew1": tmp_path / "exchange/logs/lsnew1_result.json",
        "lsnew1_policy": tmp_path / "config/lsnew1_policy.json",
        "schema_out": tmp_path / "config/schema.json",
        "template_out": tmp_path / "exchange/new_release/template.json",
        "record_out": tmp_path / "exchange/new_release/record.json",
        "simple_x_out": tmp_path / "exchange/templates/simple_x.md",
        "result_out": tmp_path / "exchange/runtime/result.json",
        "lock_out": tmp_path / "exchange/locks/lock.json",
        "report_out": tmp_path / "reports/report.md",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["lsnew1"], _base_lsnew1_result())
    _write_json(paths["lsnew1_policy"], _base_lsnew1_policy())
    return paths


def _base_flags() -> list[str]:
    return [
        "--create-candidate-schema",
        "--create-candidate-template",
        "--create-simple-x-template",
        "--require-human-input",
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


def _run(paths: dict[str, Path], extra_flags: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    flags = _base_flags() if extra_flags is None else extra_flags
    cmd = [
        sys.executable,
        SCRIPT,
        "--policy",
        str(paths["policy"]),
        "--ls-new1-result",
        str(paths["lsnew1"]),
        "--ls-new1-policy",
        str(paths["lsnew1_policy"]),
        "--candidate-schema-output",
        str(paths["schema_out"]),
        "--candidate-template-output",
        str(paths["template_out"]),
        "--candidate-record-output",
        str(paths["record_out"]),
        "--simple-x-template-output",
        str(paths["simple_x_out"]),
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


def _assert_missing_flag_failed(tmp_path: Path, missing: str) -> None:
    paths = _prepare(tmp_path)
    flags = [f for f in _base_flags() if f != missing]
    cp = _run(paths, flags)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def _run_success(tmp_path: Path) -> tuple[dict[str, Path], dict]:
    paths = _prepare(tmp_path)
    cp = _run(paths)
    assert cp.returncode == 0
    payload = _payload(paths["result_out"])
    assert payload["status"] == WAITING
    return paths, payload


# 1-16

def test_01_missing_policy_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["policy"].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_02_missing_lsnew1_result_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    paths["lsnew1"].unlink()
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_03_lsnew1_validation_mismatch_fails(tmp_path: Path) -> None:
    paths = _prepare(tmp_path)
    bad = _base_lsnew1_result()
    bad["validation_status"] = "BAD"
    _write_json(paths["lsnew1"], bad)
    cp = _run(paths)
    assert cp.returncode == 1
    assert _payload(paths["result_out"])["status"] == FAILED


def test_04_missing_create_candidate_schema_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--create-candidate-schema")


def test_05_missing_create_candidate_template_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--create-candidate-template")


def test_06_missing_create_simple_x_template_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--create-simple-x-template")


def test_07_missing_require_human_input_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-human-input")


def test_08_missing_require_no_wordpress_api_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-wordpress-api")


def test_09_missing_require_no_credential_read_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-credential-read")


def test_10_missing_require_no_external_fetch_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-external-fetch")


def test_11_missing_require_no_amazon_api_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-amazon-api")


def test_12_missing_require_no_x_api_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-x-api")


def test_13_missing_require_no_candidate_selection_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-candidate-selection")


def test_14_missing_require_no_ls_next1_fill_update_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--require-no-ls-next1-fill-update")


def test_15_missing_forbid_post119_update_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--forbid-post119-update")


def test_16_missing_forbid_post183_update_flag_fails(tmp_path: Path) -> None:
    _assert_missing_flag_failed(tmp_path, "--forbid-post183-update")


# 17-24

def test_17_valid_waiting_build(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["status"] == WAITING


def test_18_candidate_schema_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["schema_out"].exists()


def test_19_candidate_template_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["template_out"].exists()


def test_20_candidate_record_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["record_out"].exists()


def test_21_simple_x_template_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["simple_x_out"].exists()


def test_22_result_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["result_out"].exists()


def test_23_lock_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["lock_out"].exists()


def test_24_report_generated(tmp_path: Path) -> None:
    paths, _ = _run_success(tmp_path)
    assert paths["report_out"].exists()


# 25-48

def test_25_result_simple_x_template_under_280_true(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["simple_x_template_under_280"] is True


def test_26_result_human_input_required_true(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["human_input_required"] is True


def test_27_result_human_filled_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["human_filled"] is False


def test_28_result_human_confirmed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["human_confirmed"] is False


def test_29_result_candidate_intake_completed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["candidate_intake_completed"] is False


def test_30_result_ready_for_ls_new_3_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["ready_for_ls_new_3"] is False


def test_31_result_work_explanation_required_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["work_explanation_required"] is False


def test_32_result_long_work_explanation_required_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["long_work_explanation_required"] is False


def test_33_result_synopsis_required_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["synopsis_required"] is False


def test_34_result_price_comparison_required_in_x_post_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["price_comparison_required_in_x_post"] is False


def test_35_result_point_reward_rate_required_in_x_post_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["point_reward_rate_required_in_x_post"] is False


def test_36_result_store_comparison_required_in_x_post_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["store_comparison_required_in_x_post"] is False


def test_37_result_wordpress_api_call_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["wordpress_api_call_executed"] is False


def test_38_result_credential_env_read_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["credential_env_read_executed"] is False


def test_39_result_external_api_call_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["external_api_call_executed"] is False


def test_40_result_http_get_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["http_get_executed"] is False


def test_41_result_web_scraping_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["web_scraping_executed"] is False


def test_42_result_amazon_api_call_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["amazon_api_call_executed"] is False


def test_43_result_x_api_call_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["x_api_call_executed"] is False


def test_44_result_x_post_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["x_post_executed"] is False


def test_45_result_candidate_selected_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["candidate_selected"] is False


def test_46_result_ls_next1_fill_updated_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["ls_next1_fill_updated"] is False


def test_47_result_post119_update_executed_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["post119_update_executed"] is False


def test_48_result_post183_update_executed_by_this_phase_false(tmp_path: Path) -> None:
    _, payload = _run_success(tmp_path)
    assert payload["post183_update_executed_by_this_phase"] is False

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6oc0_final_execute_now_confirmation.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_base_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "confirmation": tmp_path / "exchange/human_review/confirmation.json",
        "ls6oa_ready": tmp_path / "exchange/logs/ls6oa_ready.json",
        "ls6oa_go": tmp_path / "exchange/human_review/ls6oa_go.json",
        "ls6ob_preflight": tmp_path / "exchange/runtime/ls6ob_preflight.json",
        "ls6ob_run": tmp_path / "exchange/logs/ls6ob_run.json",
        "ls6ob_validation": tmp_path / "exchange/logs/ls6ob_validation.json",
        "ls6oc1_not_ready": tmp_path / "exchange/logs/ls6oc1_not_ready.json",
        "one_shot_lock": tmp_path / "exchange/locks/one_shot_lock.json",
        "runtime_freeze_state": tmp_path / "exchange/runtime/runtime_freeze_state.json",
        "credential_presence": tmp_path / "exchange/runtime/credential_presence.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b_lock": tmp_path / "exchange/locks/ls6b_lock.json",
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6O-C-0",
            "execution_mode": "FINAL_EXECUTE_NOW_CONFIRMATION_GATE_ONLY",
            "production_status": "NO_GO",
            "target_payload": {
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "post_status": "draft",
                "content_format": "html",
                "max_items": 1,
            },
        },
    )

    write_json(
        files["confirmation"],
        {
            "phase": "LS-6O-C-0",
            "confirmation_status": "HUMAN_CONFIRMED_FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION",
            "confirmation_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            "execute_now_checklist": {
                "a": True,
                "b": True,
                "c": True,
            },
            "decision": {
                "final_execute_now_granted": True,
                "final_execute_now_consumed": False,
                "actual_execution_allowed_by_this_phase": False,
                "runner_execution_allowed_by_this_phase": False,
                "wordpress_api_call_allowed_by_this_phase": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_draft_creation_allowed_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": False,
                "requires_ls6oc1_execute_now_cli": True,
            },
            "current_phase_execution": {
                "credential_env_read_executed": False,
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "wordpress_existing_post_update_executed": False,
                "post119_update_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "actual_wordpress_go_consumed_by_this_phase": False,
                "final_execute_now_consumed_by_this_phase": False,
                "one_shot_actual_execution_lock_consumed_by_this_phase": False,
                "runtime_freeze_restored_by_this_phase": False,
                "runner_executed": False,
                "actual_execution_executed": False,
                "ls6b_rerun_executed": False,
            },
        },
    )

    write_json(
        files["ls6oa_ready"],
        {
            "status": "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION",
            "actual_wordpress_go_consumed": False,
        },
    )
    write_json(files["ls6oa_go"], {"go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY"})
    write_json(files["ls6ob_preflight"], {"runner_final_preflight_passed": True})
    write_json(files["ls6ob_run"], {"status": "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE", "runner_final_preflight_passed": True})
    write_json(files["ls6ob_validation"], {"status": "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE"})
    write_json(
        files["ls6oc1_not_ready"],
        {"status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_FINAL_EXECUTE_NOW"},
    )
    write_json(files["one_shot_lock"], {"one_shot_actual_execution_lock_active": True, "one_shot_actual_execution_lock_consumed": False})
    write_json(files["runtime_freeze_state"], {"runtime_freeze_active": True, "runtime_freeze_restored": False})
    write_json(files["credential_presence"], {"required_keys_present": True, "required_keys_non_empty": True})
    write_json(
        files["ls6c_payload"],
        {
            "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
            "payload_ready": True,
            "max_items": 1,
            "payloads": [
                {
                    "title": "2.5次元の誘惑",
                    "asin": "B07X2G67B4",
                    "post_status": "draft",
                    "content_format": "html",
                    "content": "<p>B07X2G67B4</p>",
                }
            ],
        },
    )
    write_json(files["ls6c_result"], {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY"})
    write_json(files["ls6b_lock"], {"rerun_allowed": False})
    return files


def run_validate(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(files["policy"]),
        "--confirmation",
        str(files["confirmation"]),
        "--ls6oa-ready-result",
        str(files["ls6oa_ready"]),
        "--ls6oa-go",
        str(files["ls6oa_go"]),
        "--ls6ob-preflight-result",
        str(files["ls6ob_preflight"]),
        "--ls6ob-run-result",
        str(files["ls6ob_run"]),
        "--ls6ob-validation-result",
        str(files["ls6ob_validation"]),
        "--ls6oc1-not-ready-result",
        str(files["ls6oc1_not_ready"]),
        "--one-shot-lock",
        str(files["one_shot_lock"]),
        "--runtime-freeze-state",
        str(files["runtime_freeze_state"]),
        "--credential-presence-result",
        str(files["credential_presence"]),
        "--ls6c-payload",
        str(files["ls6c_payload"]),
        "--ls6c-result",
        str(files["ls6c_result"]),
        "--ls6b-lock",
        str(files["ls6b_lock"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, text=True, capture_output=True)


def test_01_valid_confirmation_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    cp = run_validate(files)
    assert cp.returncode == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION"


def test_02_confirmation_missing_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    files["confirmation"].unlink()
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_03_wrong_confirmation_label_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["confirmation_label"] = "WRONG"
    write_json(files["confirmation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_04_final_execute_now_granted_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["decision"]["final_execute_now_granted"] = False
    write_json(files["confirmation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_05_final_execute_now_consumed_true_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["decision"]["final_execute_now_consumed"] = True
    write_json(files["confirmation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_06_checklist_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["execute_now_checklist"]["a"] = False
    write_json(files["confirmation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_07_current_phase_execution_true_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["current_phase_execution"]["runner_executed"] = True
    write_json(files["confirmation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_08_ls6oa_ready_missing_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    files["ls6oa_ready"].unlink()
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_09_actual_wordpress_go_consumed_true_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6oa_ready"])
    payload["actual_wordpress_go_consumed"] = True
    write_json(files["ls6oa_ready"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_10_ls6ob_validation_not_validated_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6ob_validation"])
    payload["status"] = "BAD"
    write_json(files["ls6ob_validation"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_11_ls6ob_runner_final_preflight_passed_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6ob_preflight"])
    payload["runner_final_preflight_passed"] = False
    write_json(files["ls6ob_preflight"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_12_ls6oc1_not_ready_guard_missing_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    files["ls6oc1_not_ready"].unlink()
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_13_ls6oc1_not_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6oc1_not_ready"])
    payload["status"] = "BAD"
    write_json(files["ls6oc1_not_ready"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_14_one_shot_lock_consumed_true_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["one_shot_lock"])
    payload["one_shot_actual_execution_lock_consumed"] = True
    write_json(files["one_shot_lock"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_15_one_shot_lock_active_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["one_shot_lock"])
    payload["one_shot_actual_execution_lock_active"] = False
    write_json(files["one_shot_lock"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_16_runtime_freeze_active_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["runtime_freeze_state"])
    payload["runtime_freeze_active"] = False
    write_json(files["runtime_freeze_state"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_17_runtime_freeze_restored_true_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["runtime_freeze_state"])
    payload["runtime_freeze_restored"] = True
    write_json(files["runtime_freeze_state"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_18_credential_presence_check_validated_false_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["credential_presence"])
    payload["required_keys_non_empty"] = False
    write_json(files["credential_presence"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_19_payload_asin_mismatch_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["asin"] = "X"
    payload["payloads"][0]["content"] = "<p>NO-ASIN</p>"
    write_json(files["ls6c_payload"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_20_post_status_not_draft_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["post_status"] = "publish"
    write_json(files["ls6c_payload"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_21_max_items_gt_one_not_ready(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["max_items"] = 2
    write_json(files["ls6c_payload"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_22_result_keeps_actual_execution_allowed_false(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    run_validate(files)
    out = read_json(files["output"])
    assert out["actual_execution_allowed"] is False


def test_23_result_keeps_wordpress_write_allowed_false(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    run_validate(files)
    out = read_json(files["output"])
    assert out["wordpress_write_allowed_by_this_phase"] is False


def test_24_result_keeps_credential_env_read_executed_false(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    run_validate(files)
    out = read_json(files["output"])
    assert out["credential_env_read_executed"] is False


def test_25_result_keeps_runner_executed_false(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    run_validate(files)
    out = read_json(files["output"])
    assert out["runner_executed"] is False


def test_26_result_next_phase_ls6oc1(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    run_validate(files)
    out = read_json(files["output"])
    assert out["next_phase"]["phase"] == "LS-6O-C-1"

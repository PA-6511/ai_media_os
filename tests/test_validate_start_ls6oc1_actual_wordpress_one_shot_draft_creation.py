from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_base_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "execution": tmp_path / "exchange/runtime/execution.json",
        "consumption": tmp_path / "exchange/locks/consumption.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "ls6oc0_ready": tmp_path / "exchange/logs/ls6oc0_ready.json",
        "ls6oc0_confirmation": tmp_path / "exchange/human_review/ls6oc0_confirmation.json",
        "ls6ob_validation": tmp_path / "exchange/logs/ls6ob_validation.json",
        "ls6oa_ready": tmp_path / "exchange/logs/ls6oa_ready.json",
        "ls6oa_go": tmp_path / "exchange/human_review/ls6oa_go.json",
        "one_shot_lock": tmp_path / "exchange/locks/one_shot_lock.json",
        "runtime_state": tmp_path / "exchange/runtime/runtime_state.json",
        "credential_presence": tmp_path / "exchange/runtime/credential_presence.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "output": tmp_path / "exchange/logs/validation_output.json",
        "report": tmp_path / "reports/validation_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6O-C-1"})
    write_json(
        files["execution"],
        {
            "phase": "LS-6O-C-1",
            "status": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATED_DRAFT_ONLY",
            "payload_title": "2.5次元の誘惑",
            "payload_asin": "B07X2G67B4",
            "requested_post_status": "draft",
            "returned_post_status": "draft",
            "new_post_id": 456,
            "new_post_link": "https://example.com/?p=456",
            "wordpress_api_call_executed": True,
            "wordpress_write_executed": True,
            "wordpress_draft_creation_executed": True,
            "wordpress_existing_post_update_executed": False,
            "post119_update_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "max_items": 1,
            "created_count": 1,
            "credential_env_read_executed": True,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
            "runtime_freeze_active": True,
            "runtime_freeze_restored": False,
            "actual_wordpress_go_consumed_by_this_phase": True,
            "final_execute_now_consumed_by_this_phase": True,
            "one_shot_actual_execution_lock_consumed_by_this_phase": True,
            "runner_executed": True,
            "actual_execution_executed": True,
            "errors": [],
        },
    )
    write_json(
        files["consumption"],
        {
            "phase": "LS-6O-C-1",
            "status": "ACTUAL_EXECUTION_CONSUMED_ONE_SHOT_LOCKS",
            "locked": True,
            "rerun_allowed": False,
            "actual_wordpress_go_consumed": True,
            "final_execute_now_consumed": True,
            "one_shot_actual_execution_lock_consumed": True,
            "created_count": 1,
            "new_post_id": 456,
            "next_phase": {"phase": "LS-6P"},
        },
    )
    write_json(
        files["run_result"],
        {"status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY"},
    )
    write_json(
        files["ls6oc0_ready"],
        {
            "status": "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION",
            "confirmation_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        },
    )
    write_json(
        files["ls6oc0_confirmation"],
        {
            "confirmation_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            "decision": {"required_confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"},
        },
    )
    write_json(
        files["policy"],
        {
            "phase": "LS-6O-C-1",
            "required_previous_phase": {"ls6oc0": {"required_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"}},
            "actual_execution_policy": {"required_confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"},
        },
    )
    write_json(files["ls6ob_validation"], {"status": "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE"})
    write_json(files["ls6oa_ready"], {"status": "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"})
    write_json(files["ls6oa_go"], {"go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY"})
    write_json(files["one_shot_lock"], {"one_shot_actual_execution_lock_active": True})
    write_json(files["runtime_state"], {"runtime_freeze_active": True, "runtime_freeze_restored": False})
    write_json(files["credential_presence"], {"required_keys_present": True, "required_keys_non_empty": True})
    write_json(
        files["ls6c_payload"],
        {
            "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
            "payloads": [{"title": "2.5次元の誘惑"}],
        },
    )
    return files


def test_validator_accepts_confirmation_label_shape(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    cp = run_validate(files)
    assert cp.returncode == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"


def run_validate(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(files["policy"]),
        "--execution-result",
        str(files["execution"]),
        "--consumption-lock",
        str(files["consumption"]),
        "--run-result",
        str(files["run_result"]),
        "--ls6oc0-ready-result",
        str(files["ls6oc0_ready"]),
        "--ls6oc0-confirmation",
        str(files["ls6oc0_confirmation"]),
        "--ls6ob-validation-result",
        str(files["ls6ob_validation"]),
        "--ls6oa-ready-result",
        str(files["ls6oa_ready"]),
        "--ls6oa-go",
        str(files["ls6oa_go"]),
        "--one-shot-lock",
        str(files["one_shot_lock"]),
        "--runtime-freeze-state",
        str(files["runtime_state"]),
        "--credential-presence-result",
        str(files["credential_presence"]),
        "--ls6c-payload",
        str(files["ls6c_payload"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_validator_valid_result(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    cp = run_validate(files)
    assert cp.returncode == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"


def test_validator_detects_new_post_id_zero(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["new_post_id"] = 0
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def test_validator_detects_returned_status_publish(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["returned_post_status"] = "publish"
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def test_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["credential_value_output"] = True
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def test_validator_detects_authorization_header_output_true(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["authorization_header_output"] = True
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def test_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["publish_executed"] = True
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def test_validator_detects_created_count_gt_one(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["execution"])
    payload["created_count"] = 2
    write_json(files["execution"], payload)
    run_validate(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"

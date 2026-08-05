from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6y_manual_publish_actual_publish_runner_execution_boundary.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6w_validation": tmp_path / "exchange/logs/ls6w_validation.json",
        "ls6w_preflight": tmp_path / "exchange/runtime/ls6w_preflight.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6Y"})

    base_run = {
        "phase": "LS-6Y",
        "status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_execution_gate_label": "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "actual_publish_execution_gate_consumed": False,
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_final_explicit_publish_execution_command": True,
        "requires_separate_actual_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6Z",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_final_explicit_publish_execution_command": True,
            "requires_separate_actual_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
    }
    write_json(files["run_result"], base_run)

    base_preflight = {
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_execution_gate_consumed": False,
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
    }
    write_json(files["preflight"], base_preflight)

    write_json(
        files["lock"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "requires_next_phase": "LS-6Z",
            "actual_publish_runner_boundary_ready": True,
            "actual_publish_runner_boundary_consumed": False,
        },
    )

    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})
    write_json(files["ls6w_validation"], {"status": "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6w_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})
    return files


def run_validator(files: dict[str, Path]) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--actual-publish-runner-boundary-preflight-result", str(files["preflight"]),
        "--actual-publish-runner-boundary-lock", str(files["lock"]),
        "--run-result", str(files["run_result"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6w-validation-result", str(files["ls6w_validation"]),
        "--ls6w-final-runner-preflight-result", str(files["ls6w_preflight"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def assert_not_ready(files: dict[str, Path]) -> None:
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_26_validator_valid_result_validated(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_27_validator_detects_wordpress_api_call_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["wordpress_api_call_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_28_validator_detects_wordpress_get_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["wordpress_get_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_29_validator_detects_wordpress_post_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["wordpress_post_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_30_validator_detects_wordpress_write_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["wordpress_write_executed_by_this_phase"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_31_validator_detects_wordpress_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["wordpress_publish_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_32_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["publish_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_33_validator_detects_manual_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["manual_publish_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_34_validator_detects_actual_publish_execution_gate_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["actual_publish_execution_gate_consumed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_35_validator_detects_actual_publish_runner_boundary_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["actual_publish_runner_boundary_consumed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_36_validator_detects_final_execution_command_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["final_execution_command_consumed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_37_validator_detects_approval_label_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["approval_label_consumed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_38_validator_detects_execute_now_confirmation_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["execute_now_confirmation_consumed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_39_validator_detects_actual_publish_execution_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["actual_publish_execution_allowed_by_this_phase"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_40_validator_detects_actual_runner_execution_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["actual_runner_execution_allowed_by_this_phase"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_41_validator_detects_credential_read_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["credential_env_read_executed"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_42_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["credential_value_output"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_43_validator_detects_authorization_header_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["authorization_header_output"] = True; write_json(f["run_result"], p)
    assert_not_ready(f)


def test_44_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["lock"]); p["rerun_allowed"] = True; write_json(f["lock"], p)
    assert_not_ready(f)


def test_45_validator_detects_next_phase_mismatch(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run_result"]); p["next_phase"]["phase"] = "LS-6Y"; write_json(f["run_result"], p)
    assert_not_ready(f)

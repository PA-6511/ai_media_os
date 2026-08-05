from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6w_manual_publish_actual_execution_final_runner_preflight.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "wp": tmp_path / "exchange/runtime/wp.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6u_validation": tmp_path / "exchange/logs/ls6u_validation.json",
        "ls6u_lock": tmp_path / "exchange/locks/ls6u_lock.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/output.md",
    }

    write_json(files["policy"], {"phase": "LS-6W"})
    write_json(
        files["wp"],
        {
            "status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED",
            "post_id": 183,
            "returned_post_status": "draft",
            "wordpress_get_executed": True,
            "wordpress_get_post_id": 183,
            "wordpress_post_executed": False,
            "wordpress_put_executed": False,
            "wordpress_patch_executed": False,
            "wordpress_delete_executed": False,
            "wordpress_write_executed_by_this_phase": False,
            "wordpress_draft_creation_executed_by_this_phase": False,
            "wordpress_publish_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "post119_update_executed": False,
        },
    )
    write_json(
        files["preflight"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH",
            "current_post_status_verified": True,
            "returned_post_status": "draft",
            "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "requires_separate_publish_execution": True,
            "publish_execution_still_blocked": True,
            "credential_env_read_executed": True,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
        },
    )
    write_json(files["lock"], {"locked": True, "rerun_allowed": False, "ls6oc1_rerun_executed": False, "requires_next_phase": "LS-6X"})
    write_json(
        files["run"],
        {
            "status": "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH",
            "post_id": 183,
            "draft_verified": True,
            "returned_post_status": "draft",
            "wordpress_get_executed": True,
            "wordpress_write_executed_by_this_phase": False,
            "wordpress_draft_creation_executed_by_this_phase": False,
            "wordpress_publish_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "post119_update_executed": False,
            "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "requires_separate_publish_execution": True,
            "publish_execution_still_blocked": True,
            "credential_env_read_executed": True,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
        },
    )

    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH"})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False, "manual_publish_executed": False}})
    write_json(files["ls6u_validation"], {"status": "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6u_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH"})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def run_validator(files: dict[str, Path]) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--wordpress-current-draft-status-result", str(files["wp"]),
        "--final-runner-preflight-result", str(files["preflight"]),
        "--final-runner-preflight-lock", str(files["lock"]),
        "--run-result", str(files["run"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6u-validation-result", str(files["ls6u_validation"]),
        "--ls6u-runner-boundary-lock", str(files["ls6u_lock"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def test_22_validator_valid_result(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_23_validator_detects_write_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["wordpress_write_executed_by_this_phase"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_24_validator_detects_publish_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["wordpress_publish_executed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_25_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["publish_executed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_26_validator_detects_manual_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["manual_publish_executed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_27_validator_detects_final_command_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["final_execution_command_consumed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_28_validator_detects_approval_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["approval_label_consumed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_29_validator_detects_execute_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["execute_now_confirmation_consumed"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_30_validator_detects_actual_runner_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["actual_runner_execution_allowed_by_this_phase"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_31_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["credential_value_output"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_32_validator_detects_authorization_header_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["authorization_header_output"] = True; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_33_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["lock"]); p["rerun_allowed"] = True; write_json(f["lock"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_34_validator_detects_returned_status_not_draft(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"]); p["returned_post_status"] = "publish"; write_json(f["run"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]


def test_35_validator_detects_next_phase_not_ls6x(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["lock"]); p["requires_next_phase"] = "LS-6Y"; write_json(f["lock"], p)
    run_validator(f)
    assert "VALIDATED" not in read_json(f["output"])["status"]

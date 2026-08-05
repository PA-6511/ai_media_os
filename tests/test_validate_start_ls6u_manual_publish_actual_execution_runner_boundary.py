from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6u_manual_publish_actual_execution_runner_boundary.py")


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
        "run": tmp_path / "exchange/logs/run.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6s_validation": tmp_path / "exchange/logs/ls6s_validation.json",
        "ls6s_preflight": tmp_path / "exchange/runtime/ls6s_preflight.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"required_previous_phase": {"ls6s": {"required_validation_status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "required_run_status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"}}})

    write_json(
        files["preflight"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH",
            "actual_runner_execution_allowed_by_this_phase": False,
        },
    )
    write_json(
        files["lock"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
        },
    )
    write_json(
        files["run"],
        {
            "status": "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
            "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
            "execute_now_confirmation_consumed": False,
            "manual_publish_runner_boundary_ready": True,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "requires_final_execution_command": True,
            "final_execution_command_required_in_next_phase": True,
            "publish_execution_still_blocked": True,
            "wordpress_api_call_executed": False,
            "wordpress_get_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
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
            "next_phase": {"phase": "LS-6V"},
        },
    )

    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6t_confirmation"], {"confirmation": {"execute_now_confirmation_consumed": False}})
    write_json(files["ls6s_validation"], {"status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6s_preflight"], {"status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})
    return files


def run_validator(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--runner-boundary-preflight-result", str(files["preflight"]),
        "--runner-boundary-lock", str(files["lock"]),
        "--run-result", str(files["run"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6s-validation-result", str(files["ls6s_validation"]),
        "--ls6s-final-preflight-result", str(files["ls6s_preflight"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_20_validator_valid_result_validated(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_21_validator_detects_wordpress_api_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["wordpress_api_call_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_22_validator_detects_wordpress_get_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["wordpress_get_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_23_validator_detects_wordpress_write_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["wordpress_write_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_24_validator_detects_wordpress_publish_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["wordpress_publish_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_25_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["publish_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_26_validator_detects_manual_publish_executed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["manual_publish_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_27_validator_detects_approval_label_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["approval_label_consumed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_28_validator_detects_execute_consumed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["execute_now_confirmation_consumed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_29_validator_detects_cred_env_read_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["credential_env_read_executed"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_30_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["credential_value_output"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_31_validator_detects_authorization_header_output_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["authorization_header_output"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_32_validator_detects_actual_runner_execution_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["actual_runner_execution_allowed_by_this_phase"] = True
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_33_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["lock"])
    p["rerun_allowed"] = True
    write_json(f["lock"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


def test_34_validator_detects_next_phase_not_ls6v(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["run"])
    p["next_phase"] = {"phase": "LS-6W"}
    write_json(f["run"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] != "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"

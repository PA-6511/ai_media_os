from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_base(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "config/policy.json",
        "run": tmp_path / "exchange/logs/run.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "ls6m_run": tmp_path / "exchange/logs/ls6m_run.json",
        "ls6m_validation": tmp_path / "exchange/logs/ls6m_validation.json",
        "cp": tmp_path / "exchange/runtime/cp.json",
        "state": tmp_path / "exchange/runtime/state.json",
        "runtime_lock": tmp_path / "exchange/locks/runtime.lock.json",
        "ls6l": tmp_path / "exchange/logs/ls6l.json",
        "ls6j": tmp_path / "exchange/logs/ls6j.json",
        "ls6i": tmp_path / "exchange/logs/ls6i.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b": tmp_path / "exchange/locks/ls6b.lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }
    write_json(paths["policy"], {"phase": "LS-6N"})
    write_json(
        paths["run"],
        {
            "status": "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE",
            "one_shot_actual_execution_lock_created": True,
            "one_shot_actual_execution_lock_active": True,
            "one_shot_actual_execution_lock_consumed": False,
            "final_execution_preflight_passed": True,
            "actual_execution_allowed": False,
            "manual_publish_allowed": False,
            "wordpress_api_call_allowed_by_this_phase": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "credential_env_read_allowed_by_this_phase": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "post119_update_executed": False,
            "publish_executed": False,
            "approval_token_consumed": False,
            "approval_label_consumed": False,
            "execute_approval_label_consumed": False,
            "separate_execution_command_consumed": False,
            "final_runtime_confirmation_consumed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
            "ls6b_rerun_executed": False,
            "credential_env_read_executed": False,
            "credential_value_output": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
            "next_phase": {"phase": "LS-6O", "execution_allowed": False},
        },
    )
    write_json(
        paths["lock"],
        {
            "status": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_CREATED_NO_CONSUMPTION_NO_WORDPRESS_WRITE",
            "locked": True,
            "one_shot_actual_execution_lock_created": True,
            "one_shot_actual_execution_lock_active": True,
            "one_shot_actual_execution_lock_consumed": False,
            "rerun_allowed": False,
        },
    )
    write_json(
        paths["preflight"],
        {
            "status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE",
            "final_execution_preflight_passed": True,
            "runtime_freeze_active": True,
            "runtime_freeze_applied": True,
            "runtime_freeze_restored": False,
            "credential_presence_check_validated": True,
            "one_shot_actual_execution_lock_consumed": False,
            "actual_execution_allowed": False,
            "wordpress_api_call_allowed_by_this_phase": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "credential_env_read_allowed_by_this_phase": False,
            "credential_env_read_executed": False,
            "credential_value_output": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
    )
    write_json(paths["ls6m_run"], {"status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE"})
    write_json(paths["ls6m_validation"], {"status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE"})
    write_json(paths["cp"], {"status": "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT"})
    write_json(paths["state"], {"runtime_freeze_active": True, "runtime_freeze_applied": True, "runtime_freeze_restored": False})
    write_json(paths["runtime_lock"], {"locked": True, "rerun_allowed": False})
    write_json(paths["ls6l"], {"status": "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"})
    write_json(paths["ls6j"], {"status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION"})
    write_json(paths["ls6i"], {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})
    write_json(paths["ls6c_payload"], {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY"})
    write_json(paths["ls6c_result"], {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"})
    write_json(paths["ls6b"], {"rerun_allowed": False})
    return paths


def run_case(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    p = {
        "policy": tmp_path / "config/policy.json",
        "run": tmp_path / "exchange/logs/run.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "ls6m_run": tmp_path / "exchange/logs/ls6m_run.json",
        "ls6m_validation": tmp_path / "exchange/logs/ls6m_validation.json",
        "cp": tmp_path / "exchange/runtime/cp.json",
        "state": tmp_path / "exchange/runtime/state.json",
        "runtime_lock": tmp_path / "exchange/locks/runtime.lock.json",
        "ls6l": tmp_path / "exchange/logs/ls6l.json",
        "ls6j": tmp_path / "exchange/logs/ls6j.json",
        "ls6i": tmp_path / "exchange/logs/ls6i.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b": tmp_path / "exchange/locks/ls6b.lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }
    if not p["policy"].exists():
        make_base(tmp_path)
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(p["policy"]),
        "--run-result",
        str(p["run"]),
        "--one-shot-lock",
        str(p["lock"]),
        "--preflight-result",
        str(p["preflight"]),
        "--ls6m-run-result",
        str(p["ls6m_run"]),
        "--ls6m-validation-result",
        str(p["ls6m_validation"]),
        "--credential-presence-result",
        str(p["cp"]),
        "--runtime-freeze-state",
        str(p["state"]),
        "--runtime-freeze-lock",
        str(p["runtime_lock"]),
        "--ls6l-ready-result",
        str(p["ls6l"]),
        "--ls6j-ready-result",
        str(p["ls6j"]),
        "--ls6i-validation-result",
        str(p["ls6i"]),
        "--ls6c-payload",
        str(p["ls6c_payload"]),
        "--ls6c-result",
        str(p["ls6c_result"]),
        "--ls6b-lock",
        str(p["ls6b"]),
        "--output",
        str(p["output"]),
        "--report",
        str(p["report"]),
    ]
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validator_valid_inputs_validated(tmp_path: Path) -> None:
    run_case(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation.json")
    assert result["status"] == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE"


def test_validator_detects_lock_consumed_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["lock"], {**read_json(p["lock"]), "one_shot_actual_execution_lock_consumed": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["lock"], {**read_json(p["lock"]), "rerun_allowed": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_preflight_actual_execution_allowed_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["preflight"], {**read_json(p["preflight"]), "actual_execution_allowed": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["preflight"], {**read_json(p["preflight"]), "credential_value_output": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_wordpress_write_executed_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["run"], {**read_json(p["run"]), "wordpress_write_executed": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_actual_execution_executed_true(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["run"], {**read_json(p["run"]), "actual_execution_executed": True})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_run_status_not_pass(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["run"], {**read_json(p["run"]), "status": "NG"})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_lock_not_locked(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["lock"], {**read_json(p["lock"]), "locked": False})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")


def test_validator_detects_preflight_status_ng(tmp_path: Path) -> None:
    p = make_base(tmp_path)
    write_json(p["preflight"], {**read_json(p["preflight"]), "status": "NG"})
    run_case(tmp_path)
    assert read_json(p["output"])["status"].endswith("NOT_READY")

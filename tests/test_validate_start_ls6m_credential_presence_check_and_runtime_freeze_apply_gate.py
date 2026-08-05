from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_policy(path: Path) -> None:
    write_json(path, {"phase": "LS-6M"})


def make_run_result(path: Path) -> None:
    write_json(
        path,
        {
            "status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE",
            "runtime_freeze_applied": True,
            "runtime_freeze_active": True,
            "runtime_freeze_restored": False,
            "one_shot_actual_execution_lock_created": False,
            "one_shot_actual_execution_lock_consumed": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
            "actual_execution_allowed": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "next_phase": {
                "phase": "LS-6N",
                "execution_allowed": False,
            },
        },
    )


def make_cp_result(path: Path) -> None:
    write_json(
        path,
        {
            "status": "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT",
            "credential_env_exists": True,
            "credential_env_is_file": True,
            "required_keys_present": True,
            "required_keys_non_empty": True,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
        },
    )


def make_freeze_state(path: Path) -> None:
    write_json(
        path,
        {
            "status": "RUNTIME_FREEZE_APPLIED_FOR_ONE_SHOT_DRAFT_CREATION_NO_WORDPRESS_WRITE",
            "runtime_freeze_applied": True,
            "runtime_freeze_active": True,
            "runtime_freeze_restored": False,
        },
    )


def make_freeze_lock(path: Path) -> None:
    write_json(path, {"locked": True, "rerun_allowed": False})


def make_ls6l(path: Path) -> None:
    write_json(path, {"status": "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"})


def make_ls6k(path: Path) -> None:
    write_json(path, {"status": "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION"})


def make_ls6j(path: Path) -> None:
    write_json(path, {"status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION"})


def make_ls6i(path: Path) -> None:
    write_json(path, {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})


def make_ls6c_payload(path: Path) -> None:
    write_json(path, {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY"})


def make_ls6c_result(path: Path) -> None:
    write_json(path, {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"})


def make_ls6b_lock(path: Path) -> None:
    write_json(path, {"rerun_allowed": False})


def run_validator(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    policy = tmp_path / "config/policy.json"
    run_result = tmp_path / "exchange/logs/run_result.json"
    cp_result = tmp_path / "exchange/runtime/cp_result.json"
    freeze_state = tmp_path / "exchange/runtime/freeze_state.json"
    freeze_lock = tmp_path / "exchange/locks/freeze_lock.json"
    ls6l = tmp_path / "exchange/logs/ls6l.json"
    ls6k = tmp_path / "exchange/logs/ls6k.json"
    ls6j = tmp_path / "exchange/logs/ls6j.json"
    ls6i = tmp_path / "exchange/logs/ls6i.json"
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    ls6c_result = tmp_path / "exchange/logs/ls6c_result.json"
    ls6b_lock = tmp_path / "exchange/locks/ls6b_lock.json"
    output = tmp_path / "exchange/logs/validation_result.json"
    report = tmp_path / "reports/validation_report.md"

    if not policy.exists():
        make_policy(policy)
    if not run_result.exists():
        make_run_result(run_result)
    if not cp_result.exists():
        make_cp_result(cp_result)
    if not freeze_state.exists():
        make_freeze_state(freeze_state)
    if not freeze_lock.exists():
        make_freeze_lock(freeze_lock)
    if not ls6l.exists():
        make_ls6l(ls6l)
    if not ls6k.exists():
        make_ls6k(ls6k)
    if not ls6j.exists():
        make_ls6j(ls6j)
    if not ls6i.exists():
        make_ls6i(ls6i)
    if not ls6c_payload.exists():
        make_ls6c_payload(ls6c_payload)
    if not ls6c_result.exists():
        make_ls6c_result(ls6c_result)
    if not ls6b_lock.exists():
        make_ls6b_lock(ls6b_lock)

    command = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(policy),
        "--run-result",
        str(run_result),
        "--credential-presence-result",
        str(cp_result),
        "--runtime-freeze-state",
        str(freeze_state),
        "--runtime-freeze-lock",
        str(freeze_lock),
        "--ls6l-ready-result",
        str(ls6l),
        "--ls6k-result",
        str(ls6k),
        "--ls6j-ready-result",
        str(ls6j),
        "--ls6i-validation-result",
        str(ls6i),
        "--ls6c-payload",
        str(ls6c_payload),
        "--ls6c-result",
        str(ls6c_result),
        "--ls6b-lock",
        str(ls6b_lock),
        "--output",
        str(output),
        "--report",
        str(report),
    ]
    return subprocess.run(command, check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validation_pass(tmp_path: Path) -> None:
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"] == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE"
    assert result["credential_presence_check_validated"] is True
    assert result["runtime_freeze_apply_validated"] is True


def test_not_ready_when_run_status_ng(tmp_path: Path) -> None:
    run_result = tmp_path / "exchange/logs/run_result.json"
    make_run_result(run_result)
    write_json(run_result, {**read_json(run_result), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_cp_status_ng(tmp_path: Path) -> None:
    cp = tmp_path / "exchange/runtime/cp_result.json"
    make_cp_result(cp)
    write_json(cp, {**read_json(cp), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_cp_required_keys_missing(tmp_path: Path) -> None:
    cp = tmp_path / "exchange/runtime/cp_result.json"
    make_cp_result(cp)
    write_json(cp, {**read_json(cp), "required_keys_present": False})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_cp_non_empty_false(tmp_path: Path) -> None:
    cp = tmp_path / "exchange/runtime/cp_result.json"
    make_cp_result(cp)
    write_json(cp, {**read_json(cp), "required_keys_non_empty": False})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_cp_secret_output_true(tmp_path: Path) -> None:
    cp = tmp_path / "exchange/runtime/cp_result.json"
    make_cp_result(cp)
    write_json(cp, {**read_json(cp), "credential_secret_output": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")
    assert any("credential_presence_result.credential_secret_output" in e for e in result["errors"])


def test_not_ready_when_runtime_state_status_ng(tmp_path: Path) -> None:
    state = tmp_path / "exchange/runtime/freeze_state.json"
    make_freeze_state(state)
    write_json(state, {**read_json(state), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_runtime_state_inactive(tmp_path: Path) -> None:
    state = tmp_path / "exchange/runtime/freeze_state.json"
    make_freeze_state(state)
    write_json(state, {**read_json(state), "runtime_freeze_active": False})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_runtime_lock_unlocked(tmp_path: Path) -> None:
    lock = tmp_path / "exchange/locks/freeze_lock.json"
    make_freeze_lock(lock)
    write_json(lock, {"locked": False, "rerun_allowed": False})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_runtime_lock_rerun_allowed_true(tmp_path: Path) -> None:
    lock = tmp_path / "exchange/locks/freeze_lock.json"
    make_freeze_lock(lock)
    write_json(lock, {"locked": True, "rerun_allowed": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_run_result_lock_created_true(tmp_path: Path) -> None:
    run_result = tmp_path / "exchange/logs/run_result.json"
    make_run_result(run_result)
    write_json(run_result, {**read_json(run_result), "one_shot_actual_execution_lock_created": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_run_result_actual_execution_true(tmp_path: Path) -> None:
    run_result = tmp_path / "exchange/logs/run_result.json"
    make_run_result(run_result)
    write_json(run_result, {**read_json(run_result), "actual_execution_executed": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_run_result_write_allowed_true(tmp_path: Path) -> None:
    run_result = tmp_path / "exchange/logs/run_result.json"
    make_run_result(run_result)
    write_json(run_result, {**read_json(run_result), "wordpress_write_allowed_by_this_phase": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_next_phase_wrong(tmp_path: Path) -> None:
    run_result = tmp_path / "exchange/logs/run_result.json"
    make_run_result(run_result)
    write_json(run_result, {**read_json(run_result), "next_phase": {"phase": "LS-X", "execution_allowed": False}})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6l_status_wrong(tmp_path: Path) -> None:
    ls6l = tmp_path / "exchange/logs/ls6l.json"
    make_ls6l(ls6l)
    write_json(ls6l, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6k_status_wrong(tmp_path: Path) -> None:
    ls6k = tmp_path / "exchange/logs/ls6k.json"
    make_ls6k(ls6k)
    write_json(ls6k, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6j_status_wrong(tmp_path: Path) -> None:
    ls6j = tmp_path / "exchange/logs/ls6j.json"
    make_ls6j(ls6j)
    write_json(ls6j, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6i_status_wrong(tmp_path: Path) -> None:
    ls6i = tmp_path / "exchange/logs/ls6i.json"
    make_ls6i(ls6i)
    write_json(ls6i, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6c_payload_status_wrong(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload)
    write_json(ls6c_payload, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6c_result_status_wrong(tmp_path: Path) -> None:
    ls6c_result = tmp_path / "exchange/logs/ls6c_result.json"
    make_ls6c_result(ls6c_result)
    write_json(ls6c_result, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6b_rerun_allowed_true(tmp_path: Path) -> None:
    ls6b = tmp_path / "exchange/locks/ls6b_lock.json"
    make_ls6b_lock(ls6b)
    write_json(ls6b, {"rerun_allowed": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_policy_phase_wrong(tmp_path: Path) -> None:
    policy = tmp_path / "config/policy.json"
    make_policy(policy)
    write_json(policy, {"phase": "LS-X"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/validation_result.json")
    assert result["status"].endswith("NOT_READY")


def test_validation_report_created(tmp_path: Path) -> None:
    run_validator(tmp_path)
    report = tmp_path / "reports/validation_report.md"
    assert report.exists()
    assert "Validation Report" in report.read_text(encoding="utf-8")

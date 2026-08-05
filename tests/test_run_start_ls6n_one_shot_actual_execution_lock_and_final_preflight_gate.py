from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/run_start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_policy(path: Path) -> None:
    write_json(
        path,
        {
            "phase": "LS-6N",
            "execution_mode": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_ONLY",
            "production_status": "NO_GO",
        },
    )


def make_ls6m_run(path: Path, *, runtime_freeze_applied: bool = True, runtime_freeze_active: bool = True) -> None:
    write_json(
        path,
        {
            "status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE",
            "runtime_freeze_applied": runtime_freeze_applied,
            "runtime_freeze_active": runtime_freeze_active,
        },
    )


def make_ls6m_validation(path: Path, *, ok: bool = True) -> None:
    status = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE" if ok else "NG"
    write_json(path, {"status": status})


def make_cp(path: Path, *, ok: bool = True) -> None:
    status = "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT" if ok else "NG"
    write_json(
        path,
        {
            "status": status,
            "required_keys_present": ok,
            "required_keys_non_empty": ok,
        },
    )


def make_runtime_state(path: Path, *, active: bool = True, applied: bool = True, restored: bool = False) -> None:
    write_json(
        path,
        {
            "runtime_freeze_active": active,
            "runtime_freeze_applied": applied,
            "runtime_freeze_restored": restored,
        },
    )


def make_runtime_lock(path: Path) -> None:
    write_json(
        path,
        {
            "locked": True,
            "runtime_freeze_active": True,
            "runtime_freeze_applied": True,
            "runtime_freeze_restored": False,
            "rerun_allowed": False,
        },
    )


def make_ls6l_ready(path: Path) -> None:
    write_json(path, {"status": "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"})


def make_ls6l_confirmation(path: Path) -> None:
    write_json(path, {"confirmation_status": "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION"})


def make_ls6k(path: Path) -> None:
    write_json(path, {"status": "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION"})


def make_ls6j_ready(path: Path) -> None:
    write_json(path, {"status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION"})


def make_ls6j_command(path: Path) -> None:
    write_json(path, {"command_status": "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION"})


def make_ls6i(path: Path) -> None:
    write_json(path, {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})


def make_ls6c_payload(path: Path, *, title: str = "2.5次元の誘惑", asin: str = "B07X2G67B4", post_status: str = "draft", payload_count: int = 1, max_items: int = 1) -> None:
    content = f'<a href="https://www.amazon.co.jp/dp/{asin}?tag=a"></a>'
    payloads = [{"title": title, "content": content, "post_status": post_status} for _ in range(payload_count)]
    write_json(
        path,
        {
            "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
            "payload_ready": True,
            "payload_count": payload_count,
            "max_items": max_items,
            "payloads": payloads,
        },
    )


def make_ls6c_result(path: Path) -> None:
    write_json(path, {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"})


def make_ls6b_lock(path: Path) -> None:
    write_json(path, {"locked": True, "rerun_allowed": False})


def run_case(tmp_path: Path, *, allow_existing: bool = False) -> subprocess.CompletedProcess[str]:
    policy = tmp_path / "config/policy.json"
    ls6m_run = tmp_path / "exchange/logs/ls6m_run.json"
    ls6m_validation = tmp_path / "exchange/logs/ls6m_validation.json"
    cp = tmp_path / "exchange/runtime/cp.json"
    state = tmp_path / "exchange/runtime/state.json"
    lock = tmp_path / "exchange/locks/runtime.lock.json"
    ls6l_ready = tmp_path / "exchange/logs/ls6l_ready.json"
    ls6l_confirmation = tmp_path / "exchange/human_review/ls6l_confirmation.json"
    ls6k = tmp_path / "exchange/logs/ls6k.json"
    ls6j_ready = tmp_path / "exchange/logs/ls6j_ready.json"
    ls6j_command = tmp_path / "exchange/human_review/ls6j_command.json"
    ls6i = tmp_path / "exchange/logs/ls6i.json"
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    ls6c_result = tmp_path / "exchange/logs/ls6c_result.json"
    ls6b_lock = tmp_path / "exchange/locks/ls6b.lock.json"
    out_lock = tmp_path / "exchange/locks/ls6n.lock.json"
    preflight = tmp_path / "exchange/runtime/preflight.json"
    output = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"

    if not policy.exists():
        make_policy(policy)
    if not ls6m_run.exists():
        make_ls6m_run(ls6m_run)
    if not ls6m_validation.exists():
        make_ls6m_validation(ls6m_validation)
    if not cp.exists():
        make_cp(cp)
    if not state.exists():
        make_runtime_state(state)
    if not lock.exists():
        make_runtime_lock(lock)
    if not ls6l_ready.exists():
        make_ls6l_ready(ls6l_ready)
    if not ls6l_confirmation.exists():
        make_ls6l_confirmation(ls6l_confirmation)
    if not ls6k.exists():
        make_ls6k(ls6k)
    if not ls6j_ready.exists():
        make_ls6j_ready(ls6j_ready)
    if not ls6j_command.exists():
        make_ls6j_command(ls6j_command)
    if not ls6i.exists():
        make_ls6i(ls6i)
    if not ls6c_payload.exists():
        make_ls6c_payload(ls6c_payload)
    if not ls6c_result.exists():
        make_ls6c_result(ls6c_result)
    if not ls6b_lock.exists():
        make_ls6b_lock(ls6b_lock)

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(policy),
        "--ls6m-run-result",
        str(ls6m_run),
        "--ls6m-validation-result",
        str(ls6m_validation),
        "--credential-presence-result",
        str(cp),
        "--runtime-freeze-state",
        str(state),
        "--runtime-freeze-lock",
        str(lock),
        "--ls6l-ready-result",
        str(ls6l_ready),
        "--ls6l-confirmation",
        str(ls6l_confirmation),
        "--ls6k-result",
        str(ls6k),
        "--ls6j-ready-result",
        str(ls6j_ready),
        "--ls6j-command",
        str(ls6j_command),
        "--ls6i-validation-result",
        str(ls6i),
        "--ls6c-payload",
        str(ls6c_payload),
        "--ls6c-result",
        str(ls6c_result),
        "--ls6b-lock",
        str(ls6b_lock),
        "--one-shot-lock-output",
        str(out_lock),
        "--preflight-output",
        str(preflight),
        "--output",
        str(output),
        "--report",
        str(report),
    ]
    if allow_existing:
        cmd.append("--allow-existing-lock-read-only")

    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_inputs_pass(tmp_path: Path) -> None:
    run_case(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    lock = read_json(tmp_path / "exchange/locks/ls6n.lock.json")
    preflight = read_json(tmp_path / "exchange/runtime/preflight.json")
    assert result["status"] == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE"
    assert lock["one_shot_actual_execution_lock_created"] is True
    assert lock["one_shot_actual_execution_lock_consumed"] is False
    assert preflight["final_execution_preflight_passed"] is True


def test_existing_lock_not_ready(tmp_path: Path) -> None:
    out_lock = tmp_path / "exchange/locks/ls6n.lock.json"
    write_json(out_lock, {"locked": True, "one_shot_actual_execution_lock_active": True})
    run_case(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_existing_lock_allow_read_only(tmp_path: Path) -> None:
    out_lock = tmp_path / "exchange/locks/ls6n.lock.json"
    original = {
        "status": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_CREATED_NO_CONSUMPTION_NO_WORDPRESS_WRITE",
        "locked": True,
        "one_shot_actual_execution_lock_created": True,
        "one_shot_actual_execution_lock_active": True,
        "one_shot_actual_execution_lock_consumed": False,
        "rerun_allowed": False,
    }
    write_json(out_lock, original)
    run_case(tmp_path, allow_existing=True)
    after = read_json(out_lock)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("PASSED_NO_WORDPRESS_WRITE")
    assert after == original


def test_ls6m_validation_not_pass_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/logs/ls6m_validation.json"
    make_ls6m_validation(p, ok=False)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_runtime_freeze_active_false_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/runtime/state.json"
    make_runtime_state(p, active=False)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_runtime_freeze_applied_false_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/runtime/state.json"
    make_runtime_state(p, applied=False)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_runtime_freeze_restored_true_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/runtime/state.json"
    make_runtime_state(p, restored=True)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_credential_presence_not_validated_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/runtime/cp.json"
    make_cp(p, ok=False)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_payload_count_over_one_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(p, payload_count=2)
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_post_status_not_draft_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(p, post_status="publish")
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_asin_mismatch_not_ready(tmp_path: Path) -> None:
    p = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(p, asin="B000000000")
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["status"].endswith("NOT_READY")


def test_one_shot_lock_created_true(tmp_path: Path) -> None:
    run_case(tmp_path)
    lock = read_json(tmp_path / "exchange/locks/ls6n.lock.json")
    assert lock["one_shot_actual_execution_lock_created"] is True


def test_one_shot_lock_consumed_false(tmp_path: Path) -> None:
    run_case(tmp_path)
    lock = read_json(tmp_path / "exchange/locks/ls6n.lock.json")
    assert lock["one_shot_actual_execution_lock_consumed"] is False


def test_final_preflight_passed_true(tmp_path: Path) -> None:
    run_case(tmp_path)
    preflight = read_json(tmp_path / "exchange/runtime/preflight.json")
    assert preflight["final_execution_preflight_passed"] is True


def test_credential_env_read_executed_false(tmp_path: Path) -> None:
    run_case(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["credential_env_read_executed"] is False


def test_wordpress_write_flags_false(tmp_path: Path) -> None:
    run_case(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["wordpress_api_call_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_draft_creation_executed"] is False


def test_runner_executed_false(tmp_path: Path) -> None:
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["runner_executed"] is False


def test_actual_execution_executed_false(tmp_path: Path) -> None:
    run_case(tmp_path)
    assert read_json(tmp_path / "exchange/logs/result.json")["actual_execution_executed"] is False

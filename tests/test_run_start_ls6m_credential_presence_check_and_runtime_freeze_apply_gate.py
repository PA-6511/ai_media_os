from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/run_start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_policy(path: Path) -> None:
    write_json(
        path,
        {
            "phase": "LS-6M",
            "execution_mode": "CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_ONLY",
            "production_status": "NO_GO",
            "credential_presence_check_policy": {
                "required_keys": [
                    "WORDPRESS_BASE_URL",
                    "WORDPRESS_USERNAME",
                    "WORDPRESS_APP_PASSWORD",
                ]
            },
        },
    )


def make_ls6l_ready(path: Path) -> None:
    write_json(
        path,
        {
            "status": "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION",
            "actual_final_runtime_confirmation": True,
            "confirmation_label": "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
            "final_runtime_confirmation_consumed": False,
        },
    )


def make_ls6l_confirmation(path: Path) -> None:
    write_json(
        path,
        {
            "confirmation_status": "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION",
            "confirmation_label": "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        },
    )


def make_ls6k_result(path: Path) -> None:
    write_json(
        path,
        {
            "status": "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION",
            "actual_execution_allowed": False,
            "runtime_freeze_plan_ready": True,
            "credential_env_read_boundary_ready": True,
            "actual_execution_lock_plan_ready": True,
        },
    )


def make_ls6k_runtime_freeze_plan(path: Path) -> None:
    write_json(path, {"status": "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION"})


def make_ls6k_credential_boundary_plan(path: Path) -> None:
    write_json(path, {"status": "CREDENTIAL_ENV_READ_BOUNDARY_DEFINED_NO_READ"})


def make_ls6k_actual_execution_lock_plan(path: Path) -> None:
    write_json(path, {"status": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION"})


def make_ls6j_ready(path: Path) -> None:
    write_json(
        path,
        {
            "status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION",
            "actual_separate_execution_command": True,
            "separate_execution_command_consumed": False,
            "actual_execution_allowed": False,
        },
    )


def make_ls6j_command(path: Path) -> None:
    write_json(
        path,
        {
            "command_status": "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION",
        },
    )


def make_ls6i_validation(path: Path) -> None:
    write_json(
        path,
        {
            "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION",
            "actual_execution_allowed": False,
        },
    )


def make_ls6c_payload(path: Path, *, title: str = "2.5次元の誘惑", asin: str = "B07X2G67B4", post_status: str = "draft", payload_count: int = 1, max_items: int = 1) -> None:
    content = f'<p><a href="https://www.amazon.co.jp/dp/{asin}?tag=a"></a></p>'
    payloads = []
    for _ in range(payload_count):
        payloads.append({"title": title, "content": content, "post_status": post_status})
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


def write_env(path: Path, *, include_base: bool = True, include_user: bool = True, include_pass: bool = True, empty_pass: bool = False) -> None:
    lines = []
    if include_base:
        lines.append("WORDPRESS_BASE_URL=https://example.com")
    if include_user:
        lines.append("WORDPRESS_USERNAME=alice")
    if include_pass:
        lines.append("WORDPRESS_APP_PASSWORD=" if empty_pass else "WORDPRESS_APP_PASSWORD=app-pass")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validator(tmp_path: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    policy = tmp_path / "config/policy.json"
    ls6l_ready = tmp_path / "exchange/logs/ls6l_ready.json"
    ls6l_confirmation = tmp_path / "exchange/human_review/ls6l_confirmation.json"
    ls6k_result = tmp_path / "exchange/logs/ls6k_result.json"
    runtime_freeze_plan = tmp_path / "exchange/runtime/ls6k_runtime_freeze_plan.json"
    credential_boundary_plan = tmp_path / "exchange/runtime/ls6k_credential_boundary_plan.json"
    actual_execution_lock_plan = tmp_path / "exchange/locks/ls6k_actual_execution_lock_plan.json"
    ls6j_ready = tmp_path / "exchange/logs/ls6j_ready.json"
    ls6j_command = tmp_path / "exchange/human_review/ls6j_command.json"
    ls6i_validation = tmp_path / "exchange/logs/ls6i_validation.json"
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    ls6c_result = tmp_path / "exchange/logs/ls6c_result.json"
    ls6b_lock = tmp_path / "exchange/locks/ls6b_lock.json"
    credential_env = tmp_path / "credential.env"

    credential_presence_output = tmp_path / "exchange/runtime/credential_presence.json"
    runtime_freeze_state_output = tmp_path / "exchange/runtime/runtime_freeze_state.json"
    runtime_freeze_lock_output = tmp_path / "exchange/locks/runtime_freeze.lock.json"
    output = tmp_path / "exchange/logs/result.json"
    report = tmp_path / "reports/report.md"

    if not policy.exists():
        make_policy(policy)
    if not ls6l_ready.exists():
        make_ls6l_ready(ls6l_ready)
    if not ls6l_confirmation.exists():
        make_ls6l_confirmation(ls6l_confirmation)
    if not ls6k_result.exists():
        make_ls6k_result(ls6k_result)
    if not runtime_freeze_plan.exists():
        make_ls6k_runtime_freeze_plan(runtime_freeze_plan)
    if not credential_boundary_plan.exists():
        make_ls6k_credential_boundary_plan(credential_boundary_plan)
    if not actual_execution_lock_plan.exists():
        make_ls6k_actual_execution_lock_plan(actual_execution_lock_plan)
    if not ls6j_ready.exists():
        make_ls6j_ready(ls6j_ready)
    if not ls6j_command.exists():
        make_ls6j_command(ls6j_command)
    if not ls6i_validation.exists():
        make_ls6i_validation(ls6i_validation)
    if not ls6c_payload.exists():
        make_ls6c_payload(ls6c_payload)
    if not ls6c_result.exists():
        make_ls6c_result(ls6c_result)
    if not ls6b_lock.exists():
        make_ls6b_lock(ls6b_lock)
    if not credential_env.exists():
        write_env(credential_env)

    command = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(policy),
        "--credential-env",
        str(credential_env),
        "--ls6l-ready-result",
        str(ls6l_ready),
        "--ls6l-confirmation",
        str(ls6l_confirmation),
        "--ls6k-result",
        str(ls6k_result),
        "--runtime-freeze-plan",
        str(runtime_freeze_plan),
        "--credential-boundary-plan",
        str(credential_boundary_plan),
        "--actual-execution-lock-plan",
        str(actual_execution_lock_plan),
        "--ls6j-ready-result",
        str(ls6j_ready),
        "--ls6j-command",
        str(ls6j_command),
        "--ls6i-validation-result",
        str(ls6i_validation),
        "--ls6c-payload",
        str(ls6c_payload),
        "--ls6c-result",
        str(ls6c_result),
        "--ls6b-lock",
        str(ls6b_lock),
        "--credential-presence-output",
        str(credential_presence_output),
        "--runtime-freeze-state-output",
        str(runtime_freeze_state_output),
        "--runtime-freeze-lock-output",
        str(runtime_freeze_lock_output),
        "--output",
        str(output),
        "--report",
        str(report),
    ]

    for key, value in overrides.items():
        command.extend([f"--{key.replace('_', '-')}", value])

    return subprocess.run(command, check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pass(tmp_path: Path) -> None:
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    cp = read_json(tmp_path / "exchange/runtime/credential_presence.json")
    runtime_state = read_json(tmp_path / "exchange/runtime/runtime_freeze_state.json")
    runtime_lock = read_json(tmp_path / "exchange/locks/runtime_freeze.lock.json")

    assert result["status"] == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE"
    assert result["credential_presence_check_executed"] is True
    assert result["runtime_freeze_applied"] is True
    assert result["runtime_freeze_active"] is True
    assert result["wordpress_write_executed"] is False
    assert cp["status"] == "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT"
    assert cp["required_keys_present"] is True
    assert cp["required_keys_non_empty"] is True
    assert runtime_state["runtime_freeze_active"] is True
    assert runtime_lock["locked"] is True


def test_not_ready_when_credential_file_missing(tmp_path: Path) -> None:
    run_validator(tmp_path, credential_env=str(tmp_path / "missing.env"))
    result = read_json(tmp_path / "exchange/logs/result.json")
    cp = read_json(tmp_path / "exchange/runtime/credential_presence.json")

    assert result["status"] == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_NOT_READY"
    assert cp["status"] == "CREDENTIAL_PRESENCE_CHECK_NOT_READY"
    assert result["runtime_freeze_applied"] is False


def test_not_ready_when_key_missing(tmp_path: Path) -> None:
    env = tmp_path / "credential.env"
    write_env(env, include_pass=False)
    run_validator(tmp_path, credential_env=str(env))
    result = read_json(tmp_path / "exchange/logs/result.json")
    cp = read_json(tmp_path / "exchange/runtime/credential_presence.json")

    assert result["status"].endswith("NOT_READY")
    assert cp["required_keys_present"] is False


def test_not_ready_when_key_empty(tmp_path: Path) -> None:
    env = tmp_path / "credential.env"
    write_env(env, empty_pass=True)
    run_validator(tmp_path, credential_env=str(env))
    cp = read_json(tmp_path / "exchange/runtime/credential_presence.json")
    result = read_json(tmp_path / "exchange/logs/result.json")

    assert cp["required_keys_non_empty"] is False
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6l_status_mismatch(tmp_path: Path) -> None:
    ls6l_ready = tmp_path / "exchange/logs/ls6l_ready.json"
    make_ls6l_ready(ls6l_ready)
    write_json(ls6l_ready, {**read_json(ls6l_ready), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")
    assert any("LS-6L ready status mismatch" in e for e in result["errors"])


def test_not_ready_when_ls6k_status_mismatch(tmp_path: Path) -> None:
    ls6k = tmp_path / "exchange/logs/ls6k_result.json"
    make_ls6k_result(ls6k)
    write_json(ls6k, {**read_json(ls6k), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6j_status_mismatch(tmp_path: Path) -> None:
    ls6j = tmp_path / "exchange/logs/ls6j_ready.json"
    make_ls6j_ready(ls6j)
    write_json(ls6j, {**read_json(ls6j), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6i_status_mismatch(tmp_path: Path) -> None:
    ls6i = tmp_path / "exchange/logs/ls6i_validation.json"
    make_ls6i_validation(ls6i)
    write_json(ls6i, {**read_json(ls6i), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6c_payload_status_mismatch(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload)
    write_json(ls6c_payload, {**read_json(ls6c_payload), "status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6c_result_status_mismatch(tmp_path: Path) -> None:
    ls6c_result = tmp_path / "exchange/logs/ls6c_result.json"
    make_ls6c_result(ls6c_result)
    write_json(ls6c_result, {"status": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_ls6b_rerun_allowed_true(tmp_path: Path) -> None:
    ls6b_lock = tmp_path / "exchange/locks/ls6b_lock.json"
    make_ls6b_lock(ls6b_lock)
    write_json(ls6b_lock, {"locked": True, "rerun_allowed": True})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_title_mismatch(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload, title="別タイトル")
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_asin_mismatch(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload, asin="B000000000")
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_post_status_not_draft(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload, post_status="publish")
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_payload_count_not_one(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload, payload_count=2)
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_max_items_not_one(tmp_path: Path) -> None:
    ls6c_payload = tmp_path / "exchange/logs/ls6c_payload.json"
    make_ls6c_payload(ls6c_payload, max_items=2)
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_policy_execution_mode_mismatch(tmp_path: Path) -> None:
    policy = tmp_path / "config/policy.json"
    make_policy(policy)
    write_json(policy, {**read_json(policy), "execution_mode": "NG"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_policy_phase_mismatch(tmp_path: Path) -> None:
    policy = tmp_path / "config/policy.json"
    make_policy(policy)
    write_json(policy, {**read_json(policy), "phase": "LS-X"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_not_ready_when_policy_production_status_mismatch(tmp_path: Path) -> None:
    policy = tmp_path / "config/policy.json"
    make_policy(policy)
    write_json(policy, {**read_json(policy), "production_status": "GO"})
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"].endswith("NOT_READY")


def test_secrets_not_output_even_on_success(tmp_path: Path) -> None:
    run_validator(tmp_path)
    result = read_json(tmp_path / "exchange/logs/result.json")
    cp = read_json(tmp_path / "exchange/runtime/credential_presence.json")

    assert result["credential_secret_output"] is False
    assert result["secret_length_output"] is False
    assert result["secret_hash_output"] is False
    assert result["authorization_header_output"] is False

    assert cp["credential_secret_output"] is False
    assert cp["secret_length_output"] is False
    assert cp["secret_hash_output"] is False
    assert cp["authorization_header_output"] is False
    serialized = json.dumps(cp, ensure_ascii=False)
    assert "app-pass" not in serialized
    assert "alice" not in serialized


def test_runtime_files_not_created_when_not_ready(tmp_path: Path) -> None:
    run_validator(tmp_path, credential_env=str(tmp_path / "missing.env"))
    assert not (tmp_path / "exchange/runtime/runtime_freeze_state.json").exists()
    assert not (tmp_path / "exchange/locks/runtime_freeze.lock.json").exists()


def test_report_is_created(tmp_path: Path) -> None:
    run_validator(tmp_path)
    report = tmp_path / "reports/report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "LS-6M Credential Presence Check" in text
    assert "status:" in text

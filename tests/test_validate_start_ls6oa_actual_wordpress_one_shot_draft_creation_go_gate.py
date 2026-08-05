from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_policy(path: Path) -> None:
    write_json(
        path,
        {
            "phase": "LS-6O-A",
            "execution_mode": "EXPLICIT_HUMAN_GO_GATE_ONLY",
            "production_status": "NO_GO",
            "explicit_human_go_policy": {
                "actual_go_file_auto_create_allowed": False,
                "human_actual_execution_go_required": True,
                "actual_execution_allowed_by_this_phase": False,
                "wordpress_api_call_allowed_by_this_phase": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_draft_creation_allowed_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": False,
                "one_shot_actual_execution_lock_consumed_by_this_phase": False,
            },
            "current_phase_safety_flags": {
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "wordpress_existing_post_update_executed": False,
                "post119_update_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "credential_env_read_executed": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "approval_token_consumed": False,
                "approval_label_consumed": False,
                "execute_approval_label_consumed": False,
                "separate_execution_command_consumed": False,
                "final_runtime_confirmation_consumed": False,
                "actual_wordpress_go_consumed": False,
                "one_shot_actual_execution_lock_consumed": False,
                "runtime_freeze_restored": False,
                "runner_executed": False,
                "actual_execution_executed": False,
                "ls6b_rerun_executed": False,
            },
        },
    )


def make_template(path: Path) -> None:
    checklist = {
        "ls6n_lock_and_final_preflight_pass_checked": "HUMAN_REQUIRED",
        "one_shot_actual_execution_lock_active_checked": "HUMAN_REQUIRED",
        "one_shot_actual_execution_lock_not_consumed_checked": "HUMAN_REQUIRED",
        "runtime_freeze_active_checked": "HUMAN_REQUIRED",
        "credential_presence_validated_checked": "HUMAN_REQUIRED",
        "target_payload_title_checked": "HUMAN_REQUIRED",
        "target_payload_asin_checked": "HUMAN_REQUIRED",
        "post_status_draft_checked": "HUMAN_REQUIRED",
        "max_items_one_checked": "HUMAN_REQUIRED",
        "no_publish_checked": "HUMAN_REQUIRED",
        "no_existing_post_update_checked": "HUMAN_REQUIRED",
        "no_post119_update_checked": "HUMAN_REQUIRED",
        "no_schedule_checked": "HUMAN_REQUIRED",
        "no_delete_checked": "HUMAN_REQUIRED",
        "single_execution_only_checked": "HUMAN_REQUIRED",
        "next_phase_still_no_write_checked": "HUMAN_REQUIRED",
    }
    write_json(
        path,
        {
            "phase": "LS-6O-A",
            "go_type": "HUMAN_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO",
            "go_status": "TEMPLATE_NOT_ACTUAL_GO",
            "go_label": "NOT_GO_YET",
            "go_checklist": checklist,
            "decision": {
                "human_actual_wordpress_one_shot_draft_creation_go_granted": False,
                "actual_wordpress_go_consumed": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_draft_creation_allowed_by_this_phase": False,
                "actual_execution_allowed_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": False,
                "one_shot_actual_execution_lock_consumed_by_this_phase": False,
            },
            "current_phase_execution": {
                "credential_env_read_executed": False,
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "runtime_freeze_restored": False,
                "one_shot_actual_execution_lock_consumed": False,
                "runner_executed": False,
                "actual_execution_executed": False,
            },
        },
    )


def make_actual_go(path: Path) -> None:
    checklist = {
        "ls6n_lock_and_final_preflight_pass_checked": True,
        "one_shot_actual_execution_lock_active_checked": True,
        "one_shot_actual_execution_lock_not_consumed_checked": True,
        "runtime_freeze_active_checked": True,
        "credential_presence_validated_checked": True,
        "target_payload_title_checked": True,
        "target_payload_asin_checked": True,
        "post_status_draft_checked": True,
        "max_items_one_checked": True,
        "no_publish_checked": True,
        "no_existing_post_update_checked": True,
        "no_post119_update_checked": True,
        "no_schedule_checked": True,
        "no_delete_checked": True,
        "single_execution_only_checked": True,
        "next_phase_still_no_write_checked": True,
    }
    write_json(
        path,
        {
            "phase": "LS-6O-A",
            "go_type": "HUMAN_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO",
            "go_status": "HUMAN_CONFIRMED_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO",
            "go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY",
            "go_checklist": checklist,
            "decision": {
                "human_actual_wordpress_one_shot_draft_creation_go_granted": True,
                "actual_wordpress_go_consumed": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_draft_creation_allowed_by_this_phase": False,
                "actual_execution_allowed_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": False,
                "one_shot_actual_execution_lock_consumed_by_this_phase": False,
            },
            "current_phase_execution": {
                "credential_env_read_executed": False,
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "runtime_freeze_restored": False,
                "one_shot_actual_execution_lock_consumed": False,
                "runner_executed": False,
                "actual_execution_executed": False,
            },
        },
    )


def make_ls6n_run(path: Path, status: str = "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE") -> None:
    write_json(path, {"status": status})


def make_ls6n_validation(path: Path, status: str = "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE") -> None:
    write_json(path, {"status": status})


def make_lock(path: Path, *, consumed: bool = False, active: bool = True, rerun_allowed: bool = False) -> None:
    write_json(
        path,
        {
            "locked": True,
            "one_shot_actual_execution_lock_created": True,
            "one_shot_actual_execution_lock_active": active,
            "one_shot_actual_execution_lock_consumed": consumed,
            "rerun_allowed": rerun_allowed,
        },
    )


def make_preflight(path: Path, *, passed: bool = True, actual_execution_allowed: bool = False, wordpress_write_allowed: bool = False) -> None:
    write_json(
        path,
        {
            "status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE",
            "final_execution_preflight_passed": passed,
            "actual_execution_allowed": actual_execution_allowed,
            "wordpress_write_allowed_by_this_phase": wordpress_write_allowed,
        },
    )


def make_ls6m_validation(path: Path, status: str = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE") -> None:
    write_json(path, {"status": status})


def make_cp(path: Path, *, valid: bool = True) -> None:
    write_json(path, {"required_keys_present": valid, "required_keys_non_empty": valid})


def make_runtime_state(path: Path, *, active: bool = True, applied: bool = True, restored: bool = False) -> None:
    write_json(path, {"runtime_freeze_active": active, "runtime_freeze_applied": applied, "runtime_freeze_restored": restored})


def make_runtime_lock(path: Path) -> None:
    write_json(path, {"locked": True})


def make_ls6l(path: Path) -> None:
    write_json(path, {"status": "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"})


def make_ls6j(path: Path) -> None:
    write_json(path, {"status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION"})


def make_ls6i(path: Path) -> None:
    write_json(path, {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})


def make_ls6c_payload(path: Path, *, payload_count: int = 1, post_status: str = "draft", title: str = "2.5次元の誘惑", asin: str = "B07X2G67B4", max_items: int = 1) -> None:
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


def make_ls6b(path: Path) -> None:
    write_json(path, {"rerun_allowed": False})


def prepare(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "go": tmp_path / "exchange/human_review/go.json",
        "ls6n_run": tmp_path / "exchange/logs/ls6n_run.json",
        "ls6n_val": tmp_path / "exchange/logs/ls6n_val.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "ls6m_val": tmp_path / "exchange/logs/ls6m_val.json",
        "cp": tmp_path / "exchange/runtime/cp.json",
        "state": tmp_path / "exchange/runtime/state.json",
        "state_lock": tmp_path / "exchange/locks/state_lock.json",
        "ls6l": tmp_path / "exchange/logs/ls6l.json",
        "ls6j": tmp_path / "exchange/logs/ls6j.json",
        "ls6i": tmp_path / "exchange/logs/ls6i.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b": tmp_path / "exchange/locks/ls6b.json",
        "output": tmp_path / "exchange/logs/result.json",
        "report": tmp_path / "reports/report.md",
    }
    make_policy(files["policy"])
    make_template(files["template"])
    make_ls6n_run(files["ls6n_run"])
    make_ls6n_validation(files["ls6n_val"])
    make_lock(files["lock"])
    make_preflight(files["preflight"])
    make_ls6m_validation(files["ls6m_val"])
    make_cp(files["cp"])
    make_runtime_state(files["state"])
    make_runtime_lock(files["state_lock"])
    make_ls6l(files["ls6l"])
    make_ls6j(files["ls6j"])
    make_ls6i(files["ls6i"])
    make_ls6c_payload(files["ls6c_payload"])
    make_ls6c_result(files["ls6c_result"])
    make_ls6b(files["ls6b"])
    return files


def run_validator(tmp_path: Path, allow_template: bool = False) -> subprocess.CompletedProcess[str]:
    f = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "go": tmp_path / "exchange/human_review/go.json",
        "ls6n_run": tmp_path / "exchange/logs/ls6n_run.json",
        "ls6n_val": tmp_path / "exchange/logs/ls6n_val.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "ls6m_val": tmp_path / "exchange/logs/ls6m_val.json",
        "cp": tmp_path / "exchange/runtime/cp.json",
        "state": tmp_path / "exchange/runtime/state.json",
        "state_lock": tmp_path / "exchange/locks/state_lock.json",
        "ls6l": tmp_path / "exchange/logs/ls6l.json",
        "ls6j": tmp_path / "exchange/logs/ls6j.json",
        "ls6i": tmp_path / "exchange/logs/ls6i.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b": tmp_path / "exchange/locks/ls6b.json",
        "output": tmp_path / "exchange/logs/result.json",
        "report": tmp_path / "reports/report.md",
    }
    if not f["policy"].exists():
        prepare(tmp_path)
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(f["policy"]),
        "--template", str(f["template"]),
        "--go", str(f["go"]),
        "--ls6n-run-result", str(f["ls6n_run"]),
        "--ls6n-validation-result", str(f["ls6n_val"]),
        "--one-shot-lock", str(f["lock"]),
        "--final-preflight-result", str(f["preflight"]),
        "--ls6m-validation-result", str(f["ls6m_val"]),
        "--credential-presence-result", str(f["cp"]),
        "--runtime-freeze-state", str(f["state"]),
        "--runtime-freeze-lock", str(f["state_lock"]),
        "--ls6l-ready-result", str(f["ls6l"]),
        "--ls6j-ready-result", str(f["ls6j"]),
        "--ls6i-validation-result", str(f["ls6i"]),
        "--ls6c-payload", str(f["ls6c_payload"]),
        "--ls6c-result", str(f["ls6c_result"]),
        "--ls6b-lock", str(f["ls6b"]),
        "--output", str(f["output"]),
        "--report", str(f["report"]),
    ]
    if allow_template:
        cmd.append("--allow-template")
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_policy_valid_and_safety_flags_false(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    policy = read_json(f["policy"])
    assert policy["phase"] == "LS-6O-A"
    assert all(v is False for v in policy["current_phase_safety_flags"].values())


def test_template_allow_template_pass(tmp_path: Path) -> None:
    run_validator(tmp_path, allow_template=True)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_TEMPLATE_PASS_NO_ACTUAL_GO"


def test_actual_go_missing_not_ready(tmp_path: Path) -> None:
    run_validator(tmp_path, allow_template=False)
    result = read_json(tmp_path / "exchange/logs/result.json")
    assert result["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_NOT_READY"


def test_valid_actual_go_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    run_validator(tmp_path)
    result = read_json(f["output"])
    assert result["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"
    assert result["actual_wordpress_go"] is True


def test_ls6n_validation_not_pass_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_ls6n_validation(f["ls6n_val"], status="NG")
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_ls6n_lock_consumed_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_lock(f["lock"], consumed=True)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_ls6n_lock_active_false_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_lock(f["lock"], active=False)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_ls6n_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_lock(f["lock"], rerun_allowed=True)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_final_preflight_passed_false_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_preflight(f["preflight"], passed=False)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_final_preflight_actual_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_preflight(f["preflight"], actual_execution_allowed=True)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_runtime_freeze_active_false_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_runtime_state(f["state"], active=False)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_runtime_freeze_restored_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_runtime_state(f["state"], restored=True)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_credential_presence_not_validated_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_cp(f["cp"], valid=False)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_ls6c_payload_count_over_one_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_ls6c_payload(f["ls6c_payload"], payload_count=2)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_ls6c_post_status_not_draft_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_ls6c_payload(f["ls6c_payload"], post_status="publish")
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_actual_go_wrong_label_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    data = read_json(f["go"])
    data["go_label"] = "WRONG"
    write_json(f["go"], data)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_actual_go_checklist_false_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    data = read_json(f["go"])
    data["go_checklist"]["no_publish_checked"] = False
    write_json(f["go"], data)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_actual_go_decision_write_allowed_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    data = read_json(f["go"])
    data["decision"]["wordpress_write_allowed_by_this_phase"] = True
    write_json(f["go"], data)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_actual_go_decision_actual_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    data = read_json(f["go"])
    data["decision"]["actual_execution_allowed_by_this_phase"] = True
    write_json(f["go"], data)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_actual_go_current_phase_execution_true_not_ready(tmp_path: Path) -> None:
    f = prepare(tmp_path)
    make_actual_go(f["go"])
    data = read_json(f["go"])
    data["current_phase_execution"]["wordpress_write_executed"] = True
    write_json(f["go"], data)
    run_validator(tmp_path)
    assert read_json(f["output"])["status"] == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


def test_result_keeps_actual_execution_allowed_false(tmp_path: Path) -> None:
    run_validator(tmp_path, allow_template=True)
    assert read_json(tmp_path / "exchange/logs/result.json")["actual_execution_allowed"] is False


def test_result_keeps_wordpress_write_allowed_false(tmp_path: Path) -> None:
    run_validator(tmp_path, allow_template=True)
    assert read_json(tmp_path / "exchange/logs/result.json")["wordpress_write_allowed_by_this_phase"] is False

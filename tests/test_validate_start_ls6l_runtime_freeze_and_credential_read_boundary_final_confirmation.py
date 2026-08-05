import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_policy.json").read_text(encoding="utf-8"))


def valid_template() -> dict[str, Any]:
    return json.loads(Path("exchange/human_review/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.template.json").read_text(encoding="utf-8"))


def valid_ls6k_result() -> dict[str, Any]:
    return {
        "phase": "LS-6K",
        "status": "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION",
        "runtime_freeze_plan_ready": True,
        "credential_env_read_boundary_ready": True,
        "actual_execution_lock_plan_ready": True,
        "actual_execution_allowed": False,
        "credential_env_read_executed": False,
        "runtime_freeze_applied": False,
        "runtime_freeze_restored": False,
    }


def valid_runtime_freeze_plan() -> dict[str, Any]:
    return {
        "phase": "LS-6K",
        "status": "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION",
        "runtime_freeze_required": True,
        "runtime_freeze_applied_by_this_phase": False,
        "runtime_freeze_restored_by_this_phase": False,
        "current_phase_execution": {
            "runtime_freeze_applied": False,
            "runtime_freeze_restored": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "actual_execution_executed": False,
        },
    }


def valid_credential_boundary_plan() -> dict[str, Any]:
    return {
        "phase": "LS-6K",
        "status": "CREDENTIAL_ENV_READ_BOUNDARY_DEFINED_NO_READ",
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_secret_output_allowed": False,
        "future_read_rules": {
            "value_output_forbidden": True,
            "length_output_forbidden": True,
            "hash_output_forbidden": True,
            "authorization_header_output_forbidden": True,
        },
        "current_phase_execution": {
            "credential_env_read_executed": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
        },
    }


def valid_execution_lock_plan() -> dict[str, Any]:
    return {
        "phase": "LS-6K",
        "status": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION",
        "one_shot_actual_execution_lock_required": True,
        "one_shot_actual_execution_lock_created_by_this_phase": False,
        "one_shot_actual_execution_lock_consumed_by_this_phase": False,
        "rerun_allowed": False,
        "current_phase_execution": {
            "one_shot_actual_execution_lock_created": False,
            "one_shot_actual_execution_lock_consumed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
            "ls6b_rerun_executed": False,
        },
    }


def valid_ls6j_ready() -> dict[str, Any]:
    return {
        "phase": "LS-6J",
        "status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION",
        "actual_separate_execution_command": True,
        "command_label": "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "separate_execution_command_consumed": False,
        "actual_execution_allowed": False,
    }


def valid_ls6j_command() -> dict[str, Any]:
    return {
        "phase": "LS-6J",
        "command_status": "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION",
        "command_label": "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
    }


def valid_ls6i_validation() -> dict[str, Any]:
    return {
        "phase": "LS-6I",
        "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION",
        "actual_execution_allowed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
    }


def valid_ls6h_result() -> dict[str, Any]:
    return {
        "phase": "LS-6H",
        "status": "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION",
        "execute_approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY",
        "execute_approval_label_consumed": False,
    }


def valid_ls6g_result() -> dict[str, Any]:
    return {
        "phase": "LS-6G",
        "status": "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION",
        "execution_allowed": False,
        "approval_label_consumed": False,
    }


def valid_ls6c_payload() -> dict[str, Any]:
    return {
        "phase": "LS-6C",
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "payload_ready": True,
        "payload_count": 1,
        "max_items": 1,
        "payloads": [
            {
                "title": "2.5次元の誘惑",
                "post_status": "draft",
                "content": "<a href=\"https://www.amazon.co.jp/dp/B07X2G67B4?tag=ktkr77-22\">Amazon</a>",
            }
        ],
    }


def valid_ls6c_result() -> dict[str, Any]:
    return {
        "phase": "LS-6C",
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY",
    }


def valid_ls6b_lock() -> dict[str, Any]:
    return {
        "phase": "LS-6B",
        "locked": True,
        "rerun_allowed": False,
    }


def valid_actual_confirmation() -> dict[str, Any]:
    return {
        "phase": "LS-6L",
        "confirmation_type": "HUMAN_FINAL_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_CONFIRMATION",
        "confirmation_status": "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION",
        "confirmation_label": "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "confirmed_by": "human",
        "confirmed_at": "2026-06-22T00:00:00+09:00",
        "target_payload": {
            "title_expected": "2.5次元の誘惑",
            "asin_expected": "B07X2G67B4",
            "post_status_expected": "draft",
            "max_items": 1,
            "payload_preview": "exchange/logs/start_ls6c_real_draft_payload_preview.json",
        },
        "confirmation_checklist": {
            "ls6k_boundary_pass_checked": True,
            "ls6j_command_ready_checked": True,
            "runtime_freeze_plan_checked": True,
            "credential_env_read_boundary_checked": True,
            "actual_execution_lock_plan_checked": True,
            "target_payload_title_checked": True,
            "target_payload_asin_checked": True,
            "max_items_one_checked": True,
            "draft_only_checked": True,
            "no_publish_checked": True,
            "no_existing_post_update_checked": True,
            "credential_values_must_not_be_output_checked": True,
            "this_phase_no_credential_read_checked": True,
            "this_phase_no_wordpress_write_checked": True,
            "next_phase_is_still_gate_checked": True,
        },
        "decision": {
            "human_final_runtime_confirmation_granted": True,
            "final_runtime_confirmation_consumed": False,
            "runtime_freeze_apply_allowed_by_this_phase": False,
            "credential_env_read_allowed_by_this_phase": False,
            "credential_presence_check_allowed_by_this_phase": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "actual_execution_allowed_by_this_phase": False,
            "requires_next_phase_credential_presence_and_freeze_apply_gate": True,
        },
        "current_phase_execution": {
            "credential_env_read_executed": False,
            "credential_presence_check_executed": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "runtime_freeze_applied": False,
            "runtime_freeze_restored": False,
            "one_shot_actual_execution_lock_created": False,
            "one_shot_actual_execution_lock_consumed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
    }


def run_validator(tmp_path: Path, overrides: dict[str, Any] | None = None, *, allow_template: bool = False, create_confirmation: bool = False) -> dict[str, Any]:
    overrides = overrides or {}

    p_policy = tmp_path / "policy.json"
    p_template = tmp_path / "template.json"
    p_confirmation = tmp_path / "confirmation.json"
    p_ls6k = tmp_path / "ls6k.json"
    p_runtime = tmp_path / "runtime.json"
    p_credential = tmp_path / "credential.json"
    p_lock_plan = tmp_path / "lock_plan.json"
    p_ls6j_ready = tmp_path / "ls6j_ready.json"
    p_ls6j_command = tmp_path / "ls6j_command.json"
    p_ls6i_validation = tmp_path / "ls6i_validation.json"
    p_ls6h_result = tmp_path / "ls6h_result.json"
    p_ls6g_result = tmp_path / "ls6g_result.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_ls6b_lock = tmp_path / "ls6b_lock.json"
    p_output = tmp_path / "result.json"
    p_report = tmp_path / "report.md"

    write_json(p_policy, overrides.get("policy", valid_policy()))
    write_json(p_template, overrides.get("template", valid_template()))
    write_json(p_ls6k, overrides.get("ls6k_result", valid_ls6k_result()))
    write_json(p_runtime, overrides.get("runtime_plan", valid_runtime_freeze_plan()))
    write_json(p_credential, overrides.get("credential_plan", valid_credential_boundary_plan()))
    write_json(p_lock_plan, overrides.get("lock_plan", valid_execution_lock_plan()))
    write_json(p_ls6j_ready, overrides.get("ls6j_ready", valid_ls6j_ready()))
    write_json(p_ls6j_command, overrides.get("ls6j_command", valid_ls6j_command()))
    write_json(p_ls6i_validation, overrides.get("ls6i_validation", valid_ls6i_validation()))
    write_json(p_ls6h_result, overrides.get("ls6h_result", valid_ls6h_result()))
    write_json(p_ls6g_result, overrides.get("ls6g_result", valid_ls6g_result()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))
    if create_confirmation:
        write_json(p_confirmation, overrides.get("confirmation", valid_actual_confirmation()))

    cmd = [
        "python3",
        "scripts/validate_start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.py",
        "--policy", str(p_policy),
        "--template", str(p_template),
        "--confirmation", str(p_confirmation),
        "--ls6k-result", str(p_ls6k),
        "--runtime-freeze-plan", str(p_runtime),
        "--credential-boundary-plan", str(p_credential),
        "--actual-execution-lock-plan", str(p_lock_plan),
        "--ls6j-ready-result", str(p_ls6j_ready),
        "--ls6j-command", str(p_ls6j_command),
        "--ls6i-validation-result", str(p_ls6i_validation),
        "--ls6h-approved-result", str(p_ls6h_result),
        "--ls6g-result", str(p_ls6g_result),
        "--ls6c-payload", str(p_ls6c_payload),
        "--ls6c-result", str(p_ls6c_result),
        "--ls6b-lock", str(p_ls6b_lock),
        "--output", str(p_output),
        "--report", str(p_report),
    ]
    if allow_template:
        cmd.append("--allow-template")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_json_valid_and_safety_flags_all_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6L"
    assert policy["execution_mode"] == "FINAL_CONFIRMATION_GATE_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_template_plus_allow_template_returns_template_pass(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_TEMPLATE_PASS_NO_ACTUAL_CONFIRMATION"


def test_actual_confirmation_missing_returns_not_ready(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6L_ACTUAL_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_CONFIRMATION_NOT_READY"


def test_valid_actual_confirmation_returns_ready(tmp_path: Path):
    result = run_validator(tmp_path, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"
    assert result["actual_final_runtime_confirmation"] is True


def test_ls6k_status_not_pass(tmp_path: Path):
    bad = valid_ls6k_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, {"ls6k_result": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_ls6k_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6k_result()
    bad["actual_execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6k_result": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_runtime_freeze_applied_true(tmp_path: Path):
    bad = valid_ls6k_result()
    bad["runtime_freeze_applied"] = True
    result = run_validator(tmp_path, {"ls6k_result": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_runtime_freeze_restored_true(tmp_path: Path):
    bad = valid_ls6k_result()
    bad["runtime_freeze_restored"] = True
    result = run_validator(tmp_path, {"ls6k_result": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_credential_env_read_executed_true(tmp_path: Path):
    bad = valid_ls6k_result()
    bad["credential_env_read_executed"] = True
    result = run_validator(tmp_path, {"ls6k_result": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_credential_boundary_value_output_forbidden_false(tmp_path: Path):
    bad = valid_credential_boundary_plan()
    bad["future_read_rules"]["value_output_forbidden"] = False
    result = run_validator(tmp_path, {"credential_plan": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_credential_boundary_authorization_header_output_forbidden_false(tmp_path: Path):
    bad = valid_credential_boundary_plan()
    bad["future_read_rules"]["authorization_header_output_forbidden"] = False
    result = run_validator(tmp_path, {"credential_plan": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_actual_execution_lock_plan_rerun_allowed_true(tmp_path: Path):
    bad = valid_execution_lock_plan()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, {"lock_plan": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_ls6j_separate_execution_command_consumed_true(tmp_path: Path):
    bad = valid_ls6j_ready()
    bad["separate_execution_command_consumed"] = True
    result = run_validator(tmp_path, {"ls6j_ready": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_ls6j_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6j_ready()
    bad["actual_execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6j_ready": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_ls6c_payload_count_gt_one(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_ls6c_post_status_not_draft(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_confirmation_label_wrong(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["confirmation_label"] = "WRONG"
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_confirmation_checklist_contains_false(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["confirmation_checklist"]["draft_only_checked"] = False
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_decision_runtime_freeze_apply_allowed_true(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["decision"]["runtime_freeze_apply_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_decision_credential_env_read_allowed_true(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["decision"]["credential_env_read_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_decision_wordpress_write_allowed_true(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["decision"]["wordpress_write_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_decision_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["decision"]["actual_execution_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_current_phase_execution_contains_true(tmp_path: Path):
    bad = valid_actual_confirmation()
    bad["current_phase_execution"]["runner_executed"] = True
    result = run_validator(tmp_path, {"confirmation": bad}, create_confirmation=True)
    assert result["status"] == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"


def test_result_keeps_actual_execution_allowed_false(tmp_path: Path):
    result = run_validator(tmp_path, create_confirmation=True)
    assert result["actual_execution_allowed"] is False

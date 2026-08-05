import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_policy.json").read_text(encoding="utf-8"))


def valid_ls6j_ready() -> dict[str, Any]:
    return {
        "status": "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION",
        "actual_separate_execution_command": True,
        "command_label": "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "separate_execution_command_consumed": False,
        "actual_execution_allowed": False,
        "next_phase": {"execution_allowed": False},
    }


def valid_ls6j_command() -> dict[str, Any]:
    return {
        "command_status": "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION",
        "command_label": "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
    }


def valid_ls6i_preflight() -> dict[str, Any]:
    return {
        "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION",
    }


def valid_ls6i_validation() -> dict[str, Any]:
    return {
        "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION",
        "runner_implemented": True,
        "runner_preflight_passed": True,
        "actual_execution_allowed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
    }


def valid_ls6h_result() -> dict[str, Any]:
    return {
        "status": "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION",
        "actual_execute_approval": True,
        "execute_approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY",
        "execute_approval_label_consumed": False,
    }


def valid_ls6h_approval() -> dict[str, Any]:
    return {"execute_approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE"}


def valid_ls6g_result() -> dict[str, Any]:
    return {
        "status": "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION",
        "final_preflight_passed": True,
        "execution_allowed": False,
    }


def valid_ls6f_plan() -> dict[str, Any]:
    return {
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "runner_executed": False,
    }


def valid_ls6f_result() -> dict[str, Any]:
    return {
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "runner_executed": False,
    }


def valid_ls6c_payload() -> dict[str, Any]:
    return {
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "payload_ready": True,
        "payload_count": 1,
        "max_items": 1,
        "payloads": [
            {
                "title": "2.5次元の誘惑",
                "post_status": "draft",
                "content_format": "html",
                "content": "<a href=\"https://www.amazon.co.jp/dp/B07X2G67B4?tag=ktkr77-22\">Amazon</a>",
                "markdown_link_present": False,
                "html_link_present": True,
                "sample_content_detected": False,
            }
        ],
    }


def valid_ls6c_result() -> dict[str, Any]:
    return {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"}


def valid_ls7a_result() -> dict[str, Any]:
    return {
        "status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED",
        "publish_decision": "DO_NOT_PUBLISH",
        "requires_payload_rebuild": True,
        "manual_publish_allowed": False,
    }


def valid_ls7a_review() -> dict[str, Any]:
    return {"review_status": "DO_NOT_PUBLISH_SAMPLE_PAYLOAD"}


def valid_ls6b_result() -> dict[str, Any]:
    return {"status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"}


def valid_ls6b_validation() -> dict[str, Any]:
    return {"validation_status": "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"}


def valid_ls6b_lock() -> dict[str, Any]:
    return {"locked": True, "rerun_allowed": False}


def valid_runtime_freeze_plan() -> dict[str, Any]:
    return {
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


def valid_credential_boundary() -> dict[str, Any]:
    return {
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


def run_validator(tmp_path: Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}

    p_policy = tmp_path / "policy.json"
    p_ls6j_ready = tmp_path / "ls6j_ready.json"
    p_ls6j_command = tmp_path / "ls6j_command.json"
    p_ls6i_pre = tmp_path / "ls6i_pre.json"
    p_ls6i_val = tmp_path / "ls6i_val.json"
    p_ls6h_result = tmp_path / "ls6h_result.json"
    p_ls6h_approval = tmp_path / "ls6h_approval.json"
    p_ls6g_result = tmp_path / "ls6g_result.json"
    p_ls6f_plan = tmp_path / "ls6f_plan.json"
    p_ls6f_result = tmp_path / "ls6f_result.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_ls7a_result = tmp_path / "ls6a_result.json"
    p_ls7a_review = tmp_path / "ls7a_review.json"
    p_ls6b_result = tmp_path / "ls6b_result.json"
    p_ls6b_validation = tmp_path / "ls6b_validation.json"
    p_ls6b_lock = tmp_path / "ls6b_lock.json"
    p_runtime = tmp_path / "runtime.json"
    p_cred = tmp_path / "cred.json"
    p_lock = tmp_path / "lock_plan.json"
    p_output = tmp_path / "result.json"
    p_report = tmp_path / "report.md"

    write_json(p_policy, overrides.get("policy", valid_policy()))
    write_json(p_ls6j_ready, overrides.get("ls6j_ready", valid_ls6j_ready()))
    write_json(p_ls6j_command, overrides.get("ls6j_command", valid_ls6j_command()))
    write_json(p_ls6i_pre, overrides.get("ls6i_pre", valid_ls6i_preflight()))
    write_json(p_ls6i_val, overrides.get("ls6i_val", valid_ls6i_validation()))
    write_json(p_ls6h_result, overrides.get("ls6h_result", valid_ls6h_result()))
    write_json(p_ls6h_approval, overrides.get("ls6h_approval", valid_ls6h_approval()))
    write_json(p_ls6g_result, overrides.get("ls6g_result", valid_ls6g_result()))
    write_json(p_ls6f_plan, overrides.get("ls6f_plan", valid_ls6f_plan()))
    write_json(p_ls6f_result, overrides.get("ls6f_result", valid_ls6f_result()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))
    write_json(p_runtime, overrides.get("runtime_plan", valid_runtime_freeze_plan()))
    write_json(p_cred, overrides.get("cred_boundary", valid_credential_boundary()))
    write_json(p_lock, overrides.get("lock_plan", valid_execution_lock_plan()))

    cmd = [
        "python3",
        "scripts/validate_start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary.py",
        "--policy", str(p_policy),
        "--ls6j-ready-result", str(p_ls6j_ready),
        "--ls6j-command", str(p_ls6j_command),
        "--ls6i-preflight-result", str(p_ls6i_pre),
        "--ls6i-validation-result", str(p_ls6i_val),
        "--ls6h-approved-result", str(p_ls6h_result),
        "--ls6h-approval", str(p_ls6h_approval),
        "--ls6g-result", str(p_ls6g_result),
        "--ls6f-runner-plan", str(p_ls6f_plan),
        "--ls6f-result", str(p_ls6f_result),
        "--ls6c-payload", str(p_ls6c_payload),
        "--ls6c-result", str(p_ls6c_result),
        "--ls7a-result", str(p_ls7a_result),
        "--ls7a-review", str(p_ls7a_review),
        "--ls6b-result", str(p_ls6b_result),
        "--ls6b-validation-result", str(p_ls6b_validation),
        "--ls6b-lock", str(p_ls6b_lock),
        "--runtime-freeze-plan", str(p_runtime),
        "--credential-boundary-plan", str(p_cred),
        "--actual-execution-lock-plan", str(p_lock),
        "--output", str(p_output),
        "--report", str(p_report),
    ]

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_and_all_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6K"
    assert policy["execution_mode"] == "FINAL_RUNNER_BOUNDARY_PREFLIGHT_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_valid_inputs_pass(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION"


def test_ls6j_status_not_ready(tmp_path: Path):
    bad = valid_ls6j_ready()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, {"ls6j_ready": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6j_command_consumed_true(tmp_path: Path):
    bad = valid_ls6j_ready()
    bad["separate_execution_command_consumed"] = True
    result = run_validator(tmp_path, {"ls6j_ready": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6j_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6j_ready()
    bad["actual_execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6j_ready": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6i_validation_status_not_pass(tmp_path: Path):
    bad = valid_ls6i_validation()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, {"ls6i_val": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6i_actual_execution_executed_true(tmp_path: Path):
    bad = valid_ls6i_validation()
    bad["actual_execution_executed"] = True
    result = run_validator(tmp_path, {"ls6i_val": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6h_execute_label_consumed_true(tmp_path: Path):
    bad = valid_ls6h_result()
    bad["execute_approval_label_consumed"] = True
    result = run_validator(tmp_path, {"ls6h_result": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6g_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6g_result()
    bad["execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6g_result": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6f_runner_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["runner_execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6f_plan": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6c_payload_count_gt_one(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6c_post_status_not_draft(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls7a_publish_decision_mismatch(tmp_path: Path):
    bad = valid_ls7a_result()
    bad["publish_decision"] = "PUBLISH"
    result = run_validator(tmp_path, {"ls7a_result": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_ls6b_lock_rerun_allowed_true(tmp_path: Path):
    bad = valid_ls6b_lock()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, {"ls6b_lock": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_runtime_freeze_applied_by_this_phase_true(tmp_path: Path):
    bad = valid_runtime_freeze_plan()
    bad["runtime_freeze_applied_by_this_phase"] = True
    result = run_validator(tmp_path, {"runtime_plan": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_runtime_freeze_restored_by_this_phase_true(tmp_path: Path):
    bad = valid_runtime_freeze_plan()
    bad["runtime_freeze_restored_by_this_phase"] = True
    result = run_validator(tmp_path, {"runtime_plan": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_credential_env_read_allowed_true(tmp_path: Path):
    bad = valid_credential_boundary()
    bad["credential_env_read_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"cred_boundary": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_credential_env_read_executed_true(tmp_path: Path):
    bad = valid_credential_boundary()
    bad["credential_env_read_executed"] = True
    result = run_validator(tmp_path, {"cred_boundary": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_lock_consumed_by_this_phase_true(tmp_path: Path):
    bad = valid_execution_lock_plan()
    bad["one_shot_actual_execution_lock_consumed_by_this_phase"] = True
    result = run_validator(tmp_path, {"lock_plan": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_policy_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_policy()
    bad["final_runner_boundary_policy"]["actual_execution_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"policy": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_policy_write_allowed_true(tmp_path: Path):
    bad = valid_policy()
    bad["final_runner_boundary_policy"]["wordpress_write_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"policy": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_policy_current_phase_safety_flag_true(tmp_path: Path):
    bad = valid_policy()
    bad["current_phase_safety_flags"]["runner_executed"] = True
    result = run_validator(tmp_path, {"policy": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_credential_value_output_forbidden_false(tmp_path: Path):
    bad = valid_credential_boundary()
    bad["future_read_rules"]["value_output_forbidden"] = False
    result = run_validator(tmp_path, {"cred_boundary": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_lock_plan_rerun_allowed_true(tmp_path: Path):
    bad = valid_execution_lock_plan()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, {"lock_plan": bad})
    assert result["status"] == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"


def test_result_keeps_actual_execution_allowed_false(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["actual_execution_allowed"] is False

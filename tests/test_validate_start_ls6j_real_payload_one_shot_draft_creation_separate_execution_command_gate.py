import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_policy.json").read_text(encoding="utf-8"))


def valid_template() -> dict[str, Any]:
    return json.loads(Path("exchange/human_review/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command.template.json").read_text(encoding="utf-8"))


def valid_ls6i_preflight() -> dict[str, Any]:
    return {
        "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION",
        "runner_implemented": True,
        "runner_preflight_passed": True,
        "actual_execution_allowed": False,
        "execute_option_implemented": False,
        "runner_executed": False,
        "actual_execution_executed": False,
    }


def valid_ls6i_validation() -> dict[str, Any]:
    return {
        "status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION",
        "runner_preflight_passed": True,
        "actual_execution_allowed": False,
        "execute_option_implemented": False,
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


def valid_command() -> dict[str, Any]:
    checklist = {k: True for k in [
        "ls6i_runner_validation_pass_checked",
        "ls6h_execute_approval_pass_checked",
        "ls6g_final_preflight_pass_checked",
        "ls6c_payload_ready_checked",
        "target_title_checked",
        "target_asin_checked",
        "target_purchase_url_checked",
        "post_status_draft_checked",
        "max_items_one_checked",
        "create_new_draft_only_checked",
        "no_existing_post_update_checked",
        "post119_not_target_checked",
        "publish_not_allowed_checked",
        "schedule_not_allowed_checked",
        "command_label_not_consumed_in_this_phase_checked",
        "wordpress_write_not_allowed_in_this_phase_checked",
    ]}
    return {
        "phase": "LS-6J",
        "command_type": "HUMAN_SEPARATE_EXECUTION_COMMAND_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
        "command_status": "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION",
        "command_label": "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "issued_by": "HUMAN",
        "issued_at": "2026-06-22T12:00:00+09:00",
        "command_checklist": checklist,
        "decision": {
            "human_separate_execution_command_granted": True,
            "separate_execution_command_consumed": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "actual_execution_allowed_by_this_phase": False,
            "credential_env_read_allowed_by_this_phase": False,
            "manual_publish_allowed": False,
            "requires_next_phase_actual_runner": True,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "wordpress_existing_post_update_executed": False,
            "post119_update_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "approval_token_consumed": False,
            "approval_label_consumed": False,
            "execute_approval_label_consumed": False,
            "separate_execution_command_consumed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
        "human_confirmation_text": "I explicitly issue a separate execution command for one future WordPress draft creation only, using the LS-6C real payload. This does not authorize publish, update, schedule, deletion, repeated execution, or any non-target payload.",
    }


def run_validator(tmp_path: Path, *, allow_template: bool = False, make_command: bool = False, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}

    p_policy = tmp_path / "policy.json"
    p_template = tmp_path / "template.json"
    p_command = tmp_path / "command.json"
    p_ls6i_pre = tmp_path / "ls6i_pre.json"
    p_ls6i_val = tmp_path / "ls6i_val.json"
    p_ls6h_result = tmp_path / "ls6h_result.json"
    p_ls6h_approval = tmp_path / "ls6h_approval.json"
    p_ls6g = tmp_path / "ls6g.json"
    p_ls6f_plan = tmp_path / "ls6f_plan.json"
    p_ls6f_result = tmp_path / "ls6f_result.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_ls7a_result = tmp_path / "ls7a_result.json"
    p_ls7a_review = tmp_path / "ls7a_review.json"
    p_ls6b_result = tmp_path / "ls6b_result.json"
    p_ls6b_validation = tmp_path / "ls6b_validation.json"
    p_ls6b_lock = tmp_path / "ls6b_lock.json"
    p_output = tmp_path / "out.json"
    p_report = tmp_path / "out.md"

    write_json(p_policy, overrides.get("policy", valid_policy()))
    write_json(p_template, overrides.get("template", valid_template()))
    write_json(p_ls6i_pre, overrides.get("ls6i_preflight", valid_ls6i_preflight()))
    write_json(p_ls6i_val, overrides.get("ls6i_validation", valid_ls6i_validation()))
    write_json(p_ls6h_result, overrides.get("ls6h_result", valid_ls6h_result()))
    write_json(p_ls6h_approval, overrides.get("ls6h_approval", valid_ls6h_approval()))
    write_json(p_ls6g, overrides.get("ls6g_result", valid_ls6g_result()))
    write_json(p_ls6f_plan, overrides.get("ls6f_plan", valid_ls6f_plan()))
    write_json(p_ls6f_result, overrides.get("ls6f_result", valid_ls6f_result()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))

    if make_command:
        write_json(p_command, overrides.get("command", valid_command()))

    cmd = [
        "python3",
        "scripts/validate_start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate.py",
        "--policy", str(p_policy),
        "--command", str(p_command),
        "--template", str(p_template),
        "--ls6i-preflight-result", str(p_ls6i_pre),
        "--ls6i-validation-result", str(p_ls6i_val),
        "--ls6h-approved-result", str(p_ls6h_result),
        "--ls6h-approval", str(p_ls6h_approval),
        "--ls6g-result", str(p_ls6g),
        "--ls6f-runner-plan", str(p_ls6f_plan),
        "--ls6f-result", str(p_ls6f_result),
        "--ls6c-payload", str(p_ls6c_payload),
        "--ls6c-result", str(p_ls6c_result),
        "--ls7a-result", str(p_ls7a_result),
        "--ls7a-review", str(p_ls7a_review),
        "--ls6b-result", str(p_ls6b_result),
        "--ls6b-validation-result", str(p_ls6b_validation),
        "--ls6b-lock", str(p_ls6b_lock),
        "--output", str(p_output),
        "--report", str(p_report),
    ]
    if allow_template:
        cmd.insert(2, "--allow-template")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_all_safety_flags_false():
    p = valid_policy()
    assert p["phase"] == "LS-6J"
    assert p["execution_mode"] == "SEPARATE_EXECUTION_COMMAND_GATE_ONLY"
    assert p["production_status"] == "NO_GO"
    for v in p["current_phase_safety_flags"].values():
        assert v is False


def test_template_allow_template_pass(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=True)
    assert result["status"] == "LS6J_SEPARATE_EXECUTION_COMMAND_TEMPLATE_PASS_NO_ACTUAL_COMMAND"


def test_missing_actual_command_not_ready(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6J_ACTUAL_SEPARATE_EXECUTION_COMMAND_NOT_READY"


def test_valid_actual_command_ready(tmp_path: Path):
    result = run_validator(tmp_path, make_command=True)
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION"


def test_ls6i_validation_status_not_pass(tmp_path: Path):
    bad = valid_ls6i_validation()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, make_command=True, overrides={"ls6i_validation": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6i_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6i_validation()
    bad["actual_execution_allowed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6i_validation": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6i_actual_execution_executed_true(tmp_path: Path):
    bad = valid_ls6i_preflight()
    bad["actual_execution_executed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6i_preflight": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6h_execute_approval_label_consumed_true(tmp_path: Path):
    bad = valid_ls6h_result()
    bad["execute_approval_label_consumed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6h_result": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6g_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6g_result()
    bad["execution_allowed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6g_result": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6f_runner_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["runner_execution_allowed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6f_plan": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6c_payload_count_gt_one(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    result = run_validator(tmp_path, make_command=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6c_post_status_not_draft(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, make_command=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_command_label_mismatch(tmp_path: Path):
    bad = valid_command()
    bad["command_label"] = "WRONG"
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_command_checklist_false(tmp_path: Path):
    bad = valid_command()
    bad["command_checklist"]["target_title_checked"] = False
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_decision_command_consumed_true(tmp_path: Path):
    bad = valid_command()
    bad["decision"]["separate_execution_command_consumed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_decision_wordpress_write_allowed_true(tmp_path: Path):
    bad = valid_command()
    bad["decision"]["wordpress_write_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_decision_actual_execution_allowed_true(tmp_path: Path):
    bad = valid_command()
    bad["decision"]["actual_execution_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_decision_credential_env_allowed_true(tmp_path: Path):
    bad = valid_command()
    bad["decision"]["credential_env_read_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_current_phase_execution_true(tmp_path: Path):
    bad = valid_command()
    bad["current_phase_execution"]["publish_executed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"command": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"


def test_ls6b_lock_rerun_allowed_true(tmp_path: Path):
    bad = valid_ls6b_lock()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, make_command=True, overrides={"ls6b_lock": bad})
    assert result["status"] == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_GATE_NOT_READY"

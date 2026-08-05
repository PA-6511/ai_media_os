import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_policy.json").read_text(encoding="utf-8"))


def valid_ls6f_plan() -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "payload_ready": True,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "payload_post_status": "draft",
        "payload_content_format": "html",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "ls6b_rerun_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "runner_executed": False,
    }


def valid_ls6f_result() -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "payload_ready": True,
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "payload_post_status": "draft",
        "payload_content_format": "html",
        "approval_label_consumed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "runner_executed": False,
    }


def valid_ls6e_result() -> dict[str, Any]:
    return {
        "status": "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
        "actual_approval": True,
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_label_consumed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
    }


def valid_ls6e_approval() -> dict[str, Any]:
    return {
        "approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
    }


def valid_ls6d_result() -> dict[str, Any]:
    return {"status": "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION", "manual_publish_allowed": False}


def valid_ls6d_review() -> dict[str, Any]:
    return {"review_status": "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD"}


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


def run_validator(tmp_path: Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    p_policy = tmp_path / "policy.json"
    p_ls6f_plan = tmp_path / "ls6f_plan.json"
    p_ls6f_result = tmp_path / "ls6f_result.json"
    p_ls6e_result = tmp_path / "ls6e_result.json"
    p_ls6e_approval = tmp_path / "ls6e_approval.json"
    p_ls6d_result = tmp_path / "ls6d_result.json"
    p_ls6d_review = tmp_path / "ls6d_review.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_ls7a_result = tmp_path / "ls7a_result.json"
    p_ls7a_review = tmp_path / "ls7a_review.json"
    p_ls6b_result = tmp_path / "ls6b_result.json"
    p_ls6b_validation = tmp_path / "ls6b_validation.json"
    p_ls6b_lock = tmp_path / "ls6b_lock.json"
    p_output = tmp_path / "result.json"
    p_report = tmp_path / "report.md"

    write_json(p_policy, overrides.get("policy", valid_policy()))
    write_json(p_ls6f_plan, overrides.get("ls6f_plan", valid_ls6f_plan()))
    write_json(p_ls6f_result, overrides.get("ls6f_result", valid_ls6f_result()))
    write_json(p_ls6e_result, overrides.get("ls6e_result", valid_ls6e_result()))
    write_json(p_ls6e_approval, overrides.get("ls6e_approval", valid_ls6e_approval()))
    write_json(p_ls6d_result, overrides.get("ls6d_result", valid_ls6d_result()))
    write_json(p_ls6d_review, overrides.get("ls6d_review", valid_ls6d_review()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))

    cmd = [
        "python3",
        "scripts/validate_start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate.py",
        "--policy", str(p_policy),
        "--ls6f-runner-plan", str(p_ls6f_plan),
        "--ls6f-result", str(p_ls6f_result),
        "--ls6e-approved-result", str(p_ls6e_result),
        "--ls6e-approval", str(p_ls6e_approval),
        "--ls6d-result", str(p_ls6d_result),
        "--ls6d-review", str(p_ls6d_review),
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
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_and_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6G"
    assert policy["execution_mode"] == "FINAL_PREFLIGHT_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_valid_full_preflight_passes(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION"


def test_ls6f_result_not_ready(tmp_path: Path):
    bad = valid_ls6f_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, {"ls6f_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6f_runner_execution_allowed_true(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["runner_execution_allowed"] = True
    result = run_validator(tmp_path, {"ls6f_plan": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6f_runner_executed_true(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["runner_executed"] = True
    result = run_validator(tmp_path, {"ls6f_plan": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6e_result_not_pass(tmp_path: Path):
    bad = valid_ls6e_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, {"ls6e_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6e_approval_label_mismatch(tmp_path: Path):
    bad = valid_ls6e_result()
    bad["approval_label"] = "WRONG"
    result = run_validator(tmp_path, {"ls6e_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6e_approval_label_consumed_true(tmp_path: Path):
    bad = valid_ls6e_result()
    bad["approval_label_consumed"] = True
    result = run_validator(tmp_path, {"ls6e_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6c_payload_count_gt_one(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6c_post_status_not_draft(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6c_markdown_link_present_true(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["markdown_link_present"] = True
    result = run_validator(tmp_path, {"ls6c_payload": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls7a_publish_decision_not_do_not_publish(tmp_path: Path):
    bad = valid_ls7a_result()
    bad["publish_decision"] = "PUBLISH"
    result = run_validator(tmp_path, {"ls7a_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_ls6b_lock_rerun_allowed_true(tmp_path: Path):
    bad = valid_ls6b_lock()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, {"ls6b_lock": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_policy_write_allowed_true_not_ready(tmp_path: Path):
    bad = valid_policy()
    bad["final_preflight_policy"]["wordpress_write_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, {"policy": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_current_phase_safety_flag_true_not_ready(tmp_path: Path):
    bad = valid_policy()
    bad["current_phase_safety_flags"]["runner_executed"] = True
    result = run_validator(tmp_path, {"policy": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_credential_env_read_executed_true_not_ready(tmp_path: Path):
    bad = valid_ls6f_result()
    bad["credential_env_read_executed"] = True
    result = run_validator(tmp_path, {"ls6f_result": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"


def test_publish_executed_true_not_ready(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["publish_executed"] = True
    result = run_validator(tmp_path, {"ls6f_plan": bad})
    assert result["status"] == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"

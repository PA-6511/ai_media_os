import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6f_real_payload_one_shot_draft_runner_prep_policy.json").read_text(encoding="utf-8"))


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


def valid_ls6d_result() -> dict[str, Any]:
    return {"status": "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION"}


def valid_ls6d_review() -> dict[str, Any]:
    return {"review_status": "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD"}


def valid_ls7a_result() -> dict[str, Any]:
    return {
        "status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED",
        "publish_decision": "DO_NOT_PUBLISH",
        "requires_payload_rebuild": True,
    }


def valid_ls7a_review() -> dict[str, Any]:
    return {"review_status": "DO_NOT_PUBLISH_SAMPLE_PAYLOAD"}


def valid_ls6b_result() -> dict[str, Any]:
    return {"status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"}


def valid_ls6b_validation() -> dict[str, Any]:
    return {"validation_status": "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"}


def valid_ls6b_lock() -> dict[str, Any]:
    return {"locked": True, "rerun_allowed": False}


def blocked_plan() -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": False,
        "runner_execution_allowed": False,
        "payload_ready": True,
        "required_previous_phase": "LS-6E",
        "missing_or_not_ready": "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
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
        "credential_env_read_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "ls6b_rerun_executed": False,
        "runner_executed": False,
        "next_phase": {
            "phase": "LS-6G",
            "execution_allowed": False,
            "requires_ls6e_actual_approval": True,
            "requires_final_preflight": True,
        },
        "errors": ["LS-6E actual approval result not ready"],
    }


def ready_plan() -> dict[str, Any]:
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
        "credential_env_read_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "ls6b_rerun_executed": False,
        "runner_executed": False,
        "next_phase": {
            "phase": "LS-6G",
            "execution_allowed": False,
            "requires_final_preflight": True,
        },
        "errors": [],
    }


def valid_ls6e_approved_result() -> dict[str, Any]:
    return {
        "status": "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_label_consumed": False,
    }


def valid_ls6e_approval() -> dict[str, Any]:
    return {
        "approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
    }


def run_validator(
    tmp_path: Path,
    *,
    plan_payload: dict[str, Any],
    with_ls6e_ready_files: bool,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}

    p_policy = tmp_path / "policy.json"
    p_plan = tmp_path / "plan.json"
    p_ls6e_result = tmp_path / "ls6e_approved_result.json"
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
    write_json(p_plan, overrides.get("plan", plan_payload))
    write_json(p_ls6d_result, overrides.get("ls6d_result", valid_ls6d_result()))
    write_json(p_ls6d_review, overrides.get("ls6d_review", valid_ls6d_review()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))

    if with_ls6e_ready_files:
        write_json(p_ls6e_result, valid_ls6e_approved_result())
        write_json(p_ls6e_approval, valid_ls6e_approval())

    cmd = [
        "python3",
        "scripts/validate_start_ls6f_real_payload_one_shot_draft_runner_prep.py",
        "--policy",
        str(p_policy),
        "--runner-plan",
        str(p_plan),
        "--ls6e-approved-result",
        str(p_ls6e_result),
        "--ls6e-approval",
        str(p_ls6e_approval),
        "--ls6d-result",
        str(p_ls6d_result),
        "--ls6d-review",
        str(p_ls6d_review),
        "--ls6c-payload",
        str(p_ls6c_payload),
        "--ls6c-result",
        str(p_ls6c_result),
        "--ls7a-result",
        str(p_ls7a_result),
        "--ls7a-review",
        str(p_ls7a_review),
        "--ls6b-result",
        str(p_ls6b_result),
        "--ls6b-validation-result",
        str(p_ls6b_validation),
        "--ls6b-lock",
        str(p_ls6b_lock),
        "--output",
        str(p_output),
        "--report",
        str(p_report),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_and_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6F"
    assert policy["execution_mode"] == "PREP_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_accept_blocked_plan(tmp_path: Path):
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False)
    assert result["status"] == "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY_RECORDED"


def test_accept_ready_plan(tmp_path: Path):
    result = run_validator(tmp_path, plan_payload=ready_plan(), with_ls6e_ready_files=True)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"


def test_ls6c_result_not_ready(tmp_path: Path):
    bad = valid_ls6c_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False, overrides={"ls6c_result": bad})
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_ls6d_result_not_pass(tmp_path: Path):
    bad = valid_ls6d_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False, overrides={"ls6d_result": bad})
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_ls7a_result_invalid(tmp_path: Path):
    bad = valid_ls7a_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False, overrides={"ls7a_result": bad})
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_ls6b_lock_rerun_allowed_true(tmp_path: Path):
    bad = valid_ls6b_lock()
    bad["rerun_allowed"] = True
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False, overrides={"ls6b_lock": bad})
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_runner_execution_allowed_true_not_ready(tmp_path: Path):
    bad_plan = blocked_plan()
    bad_plan["runner_execution_allowed"] = True
    result = run_validator(tmp_path, plan_payload=bad_plan, with_ls6e_ready_files=False)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_wordpress_write_executed_true_not_ready(tmp_path: Path):
    bad_plan = blocked_plan()
    bad_plan["wordpress_write_executed"] = True
    result = run_validator(tmp_path, plan_payload=bad_plan, with_ls6e_ready_files=False)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_credential_env_read_executed_true_not_ready(tmp_path: Path):
    bad_plan = blocked_plan()
    bad_plan["credential_env_read_executed"] = True
    result = run_validator(tmp_path, plan_payload=bad_plan, with_ls6e_ready_files=False)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_approval_label_consumed_true_not_ready(tmp_path: Path):
    bad_plan = blocked_plan()
    bad_plan["approval_label_consumed"] = True
    result = run_validator(tmp_path, plan_payload=bad_plan, with_ls6e_ready_files=False)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_payload_count_gt_one_not_ready(tmp_path: Path):
    bad_payload = valid_ls6c_payload()
    bad_payload["payload_count"] = 2
    result = run_validator(tmp_path, plan_payload=blocked_plan(), with_ls6e_ready_files=False, overrides={"ls6c_payload": bad_payload})
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"

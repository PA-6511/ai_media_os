import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6d_real_payload_human_review_gate_policy.json").read_text(encoding="utf-8"))


def valid_template() -> dict[str, Any]:
    return json.loads(Path("exchange/human_review/start_ls6d_real_payload_human_review.template.json").read_text(encoding="utf-8"))


def valid_ls6c_payload() -> dict[str, Any]:
    return {
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "payload_ready": True,
        "payload_count": 1,
        "max_items": 1,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "ls6b_rerun_executed": False,
        "payloads": [
            {
                "title": "2.5次元の誘惑",
                "post_status": "draft",
                "content_format": "html",
                "markdown_link_present": False,
                "html_link_present": True,
                "sample_content_detected": False,
                "category": "電子書籍",
                "tags": ["既刊", "電子書籍"],
            }
        ],
    }


def valid_ls6c_result() -> dict[str, Any]:
    return {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"}


def valid_ls7a_result() -> dict[str, Any]:
    return {"status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "requires_payload_rebuild": True}


def valid_ls7a_review() -> dict[str, Any]:
    return {"review_status": "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "manual_publish_allowed": False}


def valid_ls6b_result() -> dict[str, Any]:
    return {"status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"}


def valid_ls6b_validation() -> dict[str, Any]:
    return {"validation_status": "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"}


def valid_ls6b_lock() -> dict[str, Any]:
    return {"locked": True, "rerun_allowed": False}


def valid_review_pass() -> dict[str, Any]:
    checklist = {
        "title_checked": True,
        "author_checked": True,
        "volume_checked": True,
        "release_date_checked": True,
        "asin_and_purchase_url_checked": True,
        "affiliate_tag_checked": True,
        "japanese_pr_disclosure_checked": True,
        "html_link_checked": True,
        "markdown_link_absent_checked": True,
        "category_and_tags_checked": True,
        "summary_not_raw_copy_checked": True,
        "no_sample_content_checked": True,
        "wordpress_write_not_allowed_in_this_phase_checked": True,
    }
    return {
        "phase": "LS-6D",
        "review_status": "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD",
        "review_checklist": checklist,
        "decision": {
            "human_review_passed": True,
            "manual_publish_allowed": False,
            "wordpress_write_allowed_next_phase": False,
            "requires_payload_fix": False,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "wordpress_existing_post_update_executed": False,
            "post119_update_executed": False,
            "publish_executed": False,
            "delete_executed": False,
            "approval_token_consumed": False,
        },
        "human_confirmation_text": "I reviewed the LS-6C real payload preview and approve it for the next approval-gate phase only.",
    }


def valid_review_fail() -> dict[str, Any]:
    review = valid_review_pass()
    review["review_status"] = "HUMAN_REVIEW_FAILED_NEEDS_PAYLOAD_FIX"
    return review


def run_validator(tmp_path: Path, *, allow_template: bool = False, review: dict[str, Any] | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}

    p_policy = tmp_path / "policy.json"
    p_template = tmp_path / "template.json"
    p_review = tmp_path / "review.json"
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
    write_json(p_template, overrides.get("template", valid_template()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))

    if review is not None:
        write_json(p_review, review)

    cmd = [
        "python3",
        "scripts/validate_start_ls6d_real_payload_human_review_gate.py",
        "--policy",
        str(p_policy),
        "--review",
        str(p_review),
        "--template",
        str(p_template),
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
    if allow_template:
        cmd.insert(2, "--allow-template")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_and_safety_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6D"
    assert policy["execution_mode"] == "REVIEW_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_template_allow_template_passes(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=True)
    assert result["status"] == "LS6D_REVIEW_TEMPLATE_PASS_NO_ACTUAL_REVIEW"
    assert result["actual_review"] is False


def test_missing_actual_review_not_ready(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=False, review=None)
    assert result["status"] == "LS6D_HUMAN_REVIEW_NOT_READY"


def test_valid_actual_review_pass(tmp_path: Path):
    result = run_validator(tmp_path, review=valid_review_pass())
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION"
    assert result["actual_review"] is True


def test_actual_review_failed_status(tmp_path: Path):
    result = run_validator(tmp_path, review=valid_review_fail())
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_FAILED_NEEDS_FIX"


def test_ls6c_result_not_ready_fails(tmp_path: Path):
    o = {"ls6c_result": {"status": "WRONG"}}
    result = run_validator(tmp_path, allow_template=True, overrides=o)
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_ls6c_payload_markdown_link_true_fails(tmp_path: Path):
    payload = valid_ls6c_payload()
    payload["payloads"][0]["markdown_link_present"] = True
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": payload})
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_ls6c_payload_sample_content_detected_true_fails(tmp_path: Path):
    payload = valid_ls6c_payload()
    payload["payloads"][0]["sample_content_detected"] = True
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": payload})
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_review_checklist_false_fails(tmp_path: Path):
    review = valid_review_pass()
    review["review_checklist"]["title_checked"] = False
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_manual_publish_allowed_true_fails(tmp_path: Path):
    review = valid_review_pass()
    review["decision"]["manual_publish_allowed"] = True
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_wordpress_write_allowed_next_phase_true_fails(tmp_path: Path):
    review = valid_review_pass()
    review["decision"]["wordpress_write_allowed_next_phase"] = True
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_current_phase_execution_true_fails(tmp_path: Path):
    review = valid_review_pass()
    review["current_phase_execution"]["publish_executed"] = True
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"


def test_ls6b_lock_rerun_allowed_true_fails(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6b_lock": {"locked": True, "rerun_allowed": True}})
    assert result["status"] == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_GATE_NOT_READY"

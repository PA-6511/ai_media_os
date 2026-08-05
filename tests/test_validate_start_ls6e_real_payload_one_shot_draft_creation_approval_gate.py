import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_policy.json").read_text(encoding="utf-8"))


def valid_template() -> dict[str, Any]:
    return json.loads(Path("exchange/human_review/start_ls6e_real_payload_one_shot_draft_creation_approval.template.json").read_text(encoding="utf-8"))


def valid_ls6d_result() -> dict[str, Any]:
    return {
        "status": "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION",
        "actual_review": True,
        "payload_ready": True,
        "manual_publish_allowed": False,
        "wordpress_write_allowed_by_this_phase": False,
    }


def valid_ls6d_review() -> dict[str, Any]:
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
        "review_status": "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD",
        "review_checklist": checklist,
        "decision": {
            "human_review_passed": True,
            "manual_publish_allowed": False,
            "wordpress_write_allowed_next_phase": False,
            "requires_payload_fix": False,
        },
    }


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
                "content": "<p><a href=\"https://www.amazon.co.jp/dp/B07X2G67B4?tag=ktkr77-22\">Amazonで確認する</a></p>",
                "markdown_link_present": False,
                "html_link_present": True,
                "sample_content_detected": False,
            }
        ],
    }


def valid_ls6c_result() -> dict[str, Any]:
    return {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"}


def valid_ls7a_result() -> dict[str, Any]:
    return {"status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "publish_decision": "DO_NOT_PUBLISH", "requires_payload_rebuild": True}


def valid_ls7a_review() -> dict[str, Any]:
    return {"review_status": "DO_NOT_PUBLISH_SAMPLE_PAYLOAD"}


def valid_ls6b_result() -> dict[str, Any]:
    return {"status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"}


def valid_ls6b_validation() -> dict[str, Any]:
    return {"validation_status": "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"}


def valid_ls6b_lock() -> dict[str, Any]:
    return {"locked": True, "rerun_allowed": False}


def valid_approval_granted() -> dict[str, Any]:
    checklist = {
        "ls6c_payload_ready_checked": True,
        "ls6d_human_review_pass_checked": True,
        "target_title_checked": True,
        "target_asin_checked": True,
        "target_purchase_url_checked": True,
        "post_status_draft_checked": True,
        "max_items_one_checked": True,
        "no_existing_post_update_checked": True,
        "post119_not_target_checked": True,
        "publish_not_allowed_checked": True,
        "wordpress_write_not_allowed_in_this_phase_checked": True,
        "approval_label_not_consumed_in_this_phase_checked": True,
    }
    return {
        "approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_checklist": checklist,
        "decision": {
            "human_approval_granted": True,
            "approval_label_consumed": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "manual_publish_allowed": False,
            "requires_runner_preflight": True,
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
        },
        "human_confirmation_text": "I explicitly approve the reviewed LS-6C real payload for the next runner-preparation phase only. This does not authorize WordPress write, publish, update, or deletion in LS-6E.",
    }


def valid_approval_denied() -> dict[str, Any]:
    ap = valid_approval_granted()
    ap["approval_status"] = "HUMAN_DENIED_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION"
    return ap


def run_validator(tmp_path: Path, *, allow_template=False, approval: dict[str, Any] | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    p_policy = tmp_path / "policy.json"
    p_template = tmp_path / "template.json"
    p_approval = tmp_path / "approval.json"
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
    write_json(p_template, overrides.get("template", valid_template()))
    write_json(p_ls6d_result, overrides.get("ls6d_result", valid_ls6d_result()))
    write_json(p_ls6d_review, overrides.get("ls6d_review", valid_ls6d_review()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))
    write_json(p_ls7a_result, overrides.get("ls7a_result", valid_ls7a_result()))
    write_json(p_ls7a_review, overrides.get("ls7a_review", valid_ls7a_review()))
    write_json(p_ls6b_result, overrides.get("ls6b_result", valid_ls6b_result()))
    write_json(p_ls6b_validation, overrides.get("ls6b_validation", valid_ls6b_validation()))
    write_json(p_ls6b_lock, overrides.get("ls6b_lock", valid_ls6b_lock()))

    if approval is not None:
        write_json(p_approval, approval)

    cmd = [
        "python3",
        "scripts/validate_start_ls6e_real_payload_one_shot_draft_creation_approval_gate.py",
        "--policy",
        str(p_policy),
        "--approval",
        str(p_approval),
        "--template",
        str(p_template),
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
    if allow_template:
        cmd.insert(2, "--allow-template")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6E"
    assert policy["execution_mode"] == "APPROVAL_GATE_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_template_allow_template_passes(tmp_path: Path):
    result = run_validator(tmp_path, allow_template=True)
    assert result["status"] == "LS6E_APPROVAL_TEMPLATE_PASS_NO_ACTUAL_APPROVAL"


def test_missing_actual_approval_not_ready(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6E_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_valid_human_approval_passes(tmp_path: Path):
    result = run_validator(tmp_path, approval=valid_approval_granted())
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION"


def test_human_denial_status(tmp_path: Path):
    result = run_validator(tmp_path, approval=valid_approval_denied())
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_DENIED"


def test_ls6d_result_not_pass_fails(tmp_path: Path):
    bad = valid_ls6d_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6d_result": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_ls6d_review_not_pass_fails(tmp_path: Path):
    bad = valid_ls6d_review()
    bad["review_status"] = "WRONG"
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6d_review": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_ls6c_payload_not_ready_fails(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_payload_count_gt1_fails(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_target_title_mismatch_fails(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["title"] = "別タイトル"
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_target_asin_mismatch_fails(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["content"] = "<a href=\"https://www.amazon.co.jp/dp/B000000000?tag=ktkr77-22\">x</a>"
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6c_payload": bad})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_approval_label_mismatch_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["approval_label"] = "WRONG"
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_checklist_false_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["approval_checklist"]["target_title_checked"] = False
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_decision_approval_label_consumed_true_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["decision"]["approval_label_consumed"] = True
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_decision_write_allowed_true_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["decision"]["wordpress_write_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_decision_draft_creation_allowed_true_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["decision"]["wordpress_draft_creation_allowed_by_this_phase"] = True
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_current_phase_execution_true_fails(tmp_path: Path):
    ap = valid_approval_granted()
    ap["current_phase_execution"]["publish_executed"] = True
    result = run_validator(tmp_path, approval=ap)
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"


def test_ls6b_lock_rerun_allowed_true_fails(tmp_path: Path):
    lock = valid_ls6b_lock()
    lock["rerun_allowed"] = True
    result = run_validator(tmp_path, allow_template=True, overrides={"ls6b_lock": lock})
    assert result["status"] == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"

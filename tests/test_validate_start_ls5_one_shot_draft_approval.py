import json
import subprocess
from pathlib import Path


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls5_one_shot_draft_approval_policy.json").read_text(encoding="utf-8"))


def valid_approval(example: bool = True) -> dict:
    return {
        "phase": "LS-5",
        "approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_status": "EXAMPLE_NOT_ACTUAL_APPROVAL" if example else "HUMAN_APPROVED",
        "approved_by": "HUMAN_REQUIRED",
        "approval_target": {
            "next_phase": "LS-6",
            "target_payload_preview": "exchange/logs/start_ls4_wordpress_draft_payload_preview.json",
            "max_items": 1,
            "post_status": "draft",
        },
        "approved_scope": {
            "wordpress_write_allowed": True,
            "wordpress_draft_creation_allowed": True,
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "existing_post_update_allowed": False,
            "delete_allowed": False,
            "amazon_api_call_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "freeze_after_run": True,
            "rollback_pointer_required": True,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "publish_executed": False,
            "approval_token_consumed": False,
        },
        "note": "This is an example approval file only. It must not be treated as actual approval.",
    }


def valid_ls4_result() -> dict:
    return {
        "phase": "LS-4",
        "status": "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "max_items": 1,
        "payload_count": 1,
        "payloads": [
            {
                "post_status": "draft",
                "title": "Sample Volume 1",
                "content": "**PR** This page contains affiliate links.\n\nSample Volume 1\n\n[Check on Amazon](https://www.amazon.co.jp/dp/B0DUMMY001?tag=exampletag-22)\n",
                "affiliate_disclosure_present": True,
                "affiliate_link_present": True,
                "category_or_tag_present": True,
                "core_boundary_ref": None,
                "audit_observation_ref": None,
                "risk_score": None,
                "rollback_pointer": {"required": True, "status": "DRY_RUN_PLACEHOLDER"},
            }
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_validator(tmp_path: Path, approval: dict, ls4_result: dict | None = None, payload: dict | None = None, allow_example: bool = False) -> dict:
    approval_path = tmp_path / "approval.json"
    ls4_result_path = tmp_path / "ls4_result.json"
    payload_path = tmp_path / "payload.json"
    output_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"

    write_json(approval_path, approval)
    write_json(ls4_result_path, ls4_result or valid_ls4_result())
    write_json(payload_path, payload or valid_ls4_result())

    cmd = [
        "python3",
        "scripts/validate_start_ls5_one_shot_draft_approval.py",
        "--policy",
        "config/start_ls5_one_shot_draft_approval_policy.json",
        "--approval",
        str(approval_path),
        "--ls4-result",
        str(ls4_result_path),
        "--payload",
        str(payload_path),
        "--output",
        str(output_path),
        "--report",
        str(report_path),
    ]
    if allow_example:
        cmd.insert(2, "--allow-example")

    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    result = json.loads(output_path.read_text(encoding="utf-8"))
    result["_stdout"] = completed.stdout
    result["_report_path"] = str(report_path)
    return result


def test_policy_json_is_valid_and_current_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-5"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    assert policy["required_approval_label"] == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY"
    assert policy["approval_source_policy"]["human_approval_required"] is True
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_example_approval_with_allow_example_passes(tmp_path):
    result = run_validator(tmp_path, valid_approval(example=True), allow_example=True)
    assert result["status"] == "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION"
    assert result["approval_is_actual"] is False
    assert result["human_approval_required"] is True
    assert result["auto_approval_allowed"] is False
    assert result["approval_token_consumed"] is False
    assert result["next_phase"]["phase"] == "LS-6"
    assert result["next_phase"]["execution_allowed"] is False
    assert result["next_phase"]["requires_actual_human_approval"] is True


def test_example_approval_without_allow_example_not_ready(tmp_path):
    result = run_validator(tmp_path, valid_approval(example=True), allow_example=False)
    assert result["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"


def test_wrong_approval_label_not_ready(tmp_path):
    approval = valid_approval(example=True)
    approval["approval_label"] = "WRONG_LABEL"
    result = run_validator(tmp_path, approval, allow_example=True)
    assert result["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"


def test_forbidden_scope_flags_not_ready(tmp_path):
    approval = valid_approval(example=True)
    approval["approved_scope"]["publish_allowed"] = True
    result = run_validator(tmp_path, approval, allow_example=True)
    assert result["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"

    approval2 = valid_approval(example=True)
    approval2["approved_scope"]["delete_allowed"] = True
    result2 = run_validator(tmp_path, approval2, allow_example=True)
    assert result2["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"


def test_ls4_not_ready_or_payload_bad_not_ready(tmp_path):
    ls4_result = valid_ls4_result()
    ls4_result["status"] = "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"
    result = run_validator(tmp_path, valid_approval(example=True), ls4_result=ls4_result, allow_example=True)
    assert result["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"

    payload = valid_ls4_result()
    payload["payloads"][0]["post_status"] = "publish"
    result2 = run_validator(tmp_path, valid_approval(example=True), payload=payload, allow_example=True)
    assert result2["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"

    payload2 = valid_ls4_result()
    payload2["payloads"].append(valid_ls4_result()["payloads"][0])
    payload2["max_items"] = 2
    result3 = run_validator(tmp_path, valid_approval(example=True), payload=payload2, allow_example=True)
    assert result3["status"] == "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"
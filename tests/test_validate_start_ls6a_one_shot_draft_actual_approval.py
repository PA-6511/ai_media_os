import json
import subprocess
from pathlib import Path


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls6a_one_shot_draft_actual_approval_policy.json").read_text(encoding="utf-8"))


def valid_template() -> dict:
    return json.loads(Path("exchange/human_review/start_ls6a_one_shot_draft_actual_approval.template.json").read_text(encoding="utf-8"))


def valid_ls3_result() -> dict:
    return {
        "phase": "LS-3",
        "status": "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
    }


def valid_ls4_result() -> dict:
    return {
        "phase": "LS-4",
        "status": "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
    }


def valid_ls5_result() -> dict:
    return {
        "phase": "LS-5",
        "status": "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
    }


def valid_payload() -> dict:
    return {
        "phase": "LS-4",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "max_items": 1,
        "payloads": [
            {
                "post_status": "draft",
                "title": "Sample Volume 1",
                "content": "sample",
            }
        ],
    }


def valid_actual_approval() -> dict:
    return {
        "phase": "LS-6A",
        "approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_status": "HUMAN_APPROVED",
        "approved_by": "HUMAN",
        "approval_created_at": "2026-06-21T12:00:00+09:00",
        "approval_target": {
            "next_phase": "LS-6B",
            "target_payload_preview": "exchange/logs/start_ls4_wordpress_draft_payload_preview.json",
            "target_ls4_result": "exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json",
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
        "human_confirmation_text": "I explicitly approve LS-6B WordPress one-shot draft creation only.",
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_validator(tmp_path: Path, allow_template: bool = False, approval: dict | None = None, *, ls3: dict | None = None, ls4: dict | None = None, ls5: dict | None = None, payload: dict | None = None) -> dict:
    policy_path = tmp_path / "policy.json"
    template_path = tmp_path / "template.json"
    approval_path = tmp_path / "approval.json"
    ls3_path = tmp_path / "ls3_result.json"
    ls4_path = tmp_path / "ls4_result.json"
    ls5_path = tmp_path / "ls5_result.json"
    payload_path = tmp_path / "payload.json"
    output_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"

    write_json(policy_path, valid_policy())
    write_json(template_path, valid_template())
    write_json(ls3_path, ls3 or valid_ls3_result())
    write_json(ls4_path, ls4 or valid_ls4_result())
    write_json(ls5_path, ls5 or valid_ls5_result())
    write_json(payload_path, payload or valid_payload())
    if approval is not None:
        write_json(approval_path, approval)

    cmd = [
        "python3",
        "scripts/validate_start_ls6a_one_shot_draft_actual_approval.py",
        "--policy",
        str(policy_path),
        "--approval",
        str(approval_path),
        "--template",
        str(template_path),
        "--ls3-result",
        str(ls3_path),
        "--ls4-result",
        str(ls4_path),
        "--ls5-result",
        str(ls5_path),
        "--payload",
        str(payload_path),
        "--output",
        str(output_path),
        "--report",
        str(report_path),
    ]
    if allow_template:
        cmd.insert(2, "--allow-template")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_policy_json_is_valid_and_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6A"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    assert policy["required_approval_label"] == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY"
    assert policy["required_approval_status"] == "HUMAN_APPROVED"
    assert policy["approval_source_policy"]["human_approval_required"] is True
    assert policy["approval_source_policy"]["auto_approval_allowed"] is False
    assert policy["approval_source_policy"]["core_ai_self_approval_allowed"] is False
    assert policy["approval_source_policy"]["block_ai_self_approval_allowed"] is False
    assert policy["approval_source_policy"]["audit_block_ai_approval_allowed"] is False
    assert policy["approval_source_policy"]["template_must_not_be_treated_as_actual"] is True
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_template_allow_template_passes(tmp_path):
    result = run_validator(tmp_path, allow_template=True)
    assert result["status"] == "LS6A_TEMPLATE_PASS_NO_ACTUAL_APPROVAL"
    assert result["approval_is_actual"] is False
    assert result["next_phase"]["execution_allowed"] is False


def test_missing_actual_approval_is_not_ready(tmp_path):
    result = run_validator(tmp_path, allow_template=False, approval=None)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_valid_actual_approval_ready_no_execution(tmp_path):
    result = run_validator(tmp_path, approval=valid_actual_approval())
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION"
    assert result["approval_is_actual"] is True


def test_wrong_approval_label_not_ready(tmp_path):
    approval = valid_actual_approval()
    approval["approval_label"] = "WRONG_LABEL"
    result = run_validator(tmp_path, approval=approval)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_wrong_human_confirmation_text_not_ready(tmp_path):
    approval = valid_actual_approval()
    approval["human_confirmation_text"] = "WRONG_TEXT"
    result = run_validator(tmp_path, approval=approval)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_forbidden_publish_or_delete_scope_not_ready(tmp_path):
    approval = valid_actual_approval()
    approval["approved_scope"]["publish_allowed"] = True
    result = run_validator(tmp_path, approval=approval)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

    approval2 = valid_actual_approval()
    approval2["approved_scope"]["delete_allowed"] = True
    result2 = run_validator(tmp_path, approval=approval2)
    assert result2["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_invalid_previous_status_not_ready(tmp_path):
    bad_ls3 = valid_ls3_result()
    bad_ls3["status"] = "WRONG"
    result = run_validator(tmp_path, approval=valid_actual_approval(), ls3=bad_ls3)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

    bad_ls4 = valid_ls4_result()
    bad_ls4["status"] = "WRONG"
    result2 = run_validator(tmp_path, approval=valid_actual_approval(), ls4=bad_ls4)
    assert result2["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

    bad_ls5 = valid_ls5_result()
    bad_ls5["status"] = "WRONG"
    result3 = run_validator(tmp_path, approval=valid_actual_approval(), ls5=bad_ls5)
    assert result3["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"


def test_invalid_payload_post_status_or_count_not_ready(tmp_path):
    payload = valid_payload()
    payload["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, approval=valid_actual_approval(), payload=payload)
    assert result["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

    payload2 = valid_payload()
    payload2["payloads"].append({"post_status": "draft", "title": "2", "content": "2"})
    payload2["max_items"] = 2
    result2 = run_validator(tmp_path, approval=valid_actual_approval(), payload=payload2)
    assert result2["status"] == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

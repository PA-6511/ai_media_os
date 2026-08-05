import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_prep_policy": {
            "runner_plan_only": True,
            "runner_execution_allowed_by_this_phase": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "credential_env_read_allowed_by_this_phase": False,
            "approval_label_consumed_by_this_phase": False,
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
        },
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


def valid_ls6e_approved_result() -> dict[str, Any]:
    return {
        "status": "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_label_consumed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
    }


def valid_ls6e_approval() -> dict[str, Any]:
    return {
        "approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
        "approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
        "decision": {
            "approval_label_consumed": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
        },
    }


def run_prepare(
    tmp_path: Path,
    *,
    create_ls6e_files: bool,
    payload: dict[str, Any] | None = None,
    payload_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p_policy = tmp_path / "policy.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_ls6e_result = tmp_path / "ls6e_approved_result.json"
    p_ls6e_approval = tmp_path / "ls6e_approval.json"
    p_output = tmp_path / "plan.json"

    write_json(p_policy, valid_policy())
    write_json(p_ls6c_payload, payload or valid_ls6c_payload())
    write_json(p_ls6c_result, payload_result or valid_ls6c_result())

    if create_ls6e_files:
        write_json(p_ls6e_result, valid_ls6e_approved_result())
        write_json(p_ls6e_approval, valid_ls6e_approval())

    cmd = [
        "python3",
        "scripts/prepare_start_ls6f_real_payload_one_shot_draft_runner.py",
        "--policy",
        str(p_policy),
        "--ls6e-approved-result",
        str(p_ls6e_result),
        "--ls6e-approval",
        str(p_ls6e_approval),
        "--ls6c-payload",
        str(p_ls6c_payload),
        "--ls6c-result",
        str(p_ls6c_result),
        "--output",
        str(p_output),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(p_output.read_text(encoding="utf-8"))


def test_blocked_when_ls6e_approved_result_missing(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=False)
    assert result["status"] == "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY"


def test_ready_when_ls6e_approved_result_present(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=True)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"


def test_not_ready_when_ls6c_not_ready(tmp_path: Path):
    bad_result = {"status": "WRONG"}
    result = run_prepare(tmp_path, create_ls6e_files=False, payload_result=bad_result)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_not_ready_when_payload_count_gt_one(tmp_path: Path):
    bad_payload = valid_ls6c_payload()
    bad_payload["payload_count"] = 2
    result = run_prepare(tmp_path, create_ls6e_files=False, payload=bad_payload)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_not_ready_when_post_status_not_draft(tmp_path: Path):
    bad_payload = valid_ls6c_payload()
    bad_payload["payloads"][0]["post_status"] = "publish"
    result = run_prepare(tmp_path, create_ls6e_files=False, payload=bad_payload)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_not_ready_when_content_format_not_html(tmp_path: Path):
    bad_payload = valid_ls6c_payload()
    bad_payload["payloads"][0]["content_format"] = "markdown"
    result = run_prepare(tmp_path, create_ls6e_files=False, payload=bad_payload)
    assert result["status"] == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"


def test_runner_plan_wordpress_flags_false(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=False)
    assert result["wordpress_api_call_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_draft_creation_executed"] is False


def test_approval_label_not_consumed(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=False)
    assert result["approval_label_consumed"] is False


def test_credential_env_not_read(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=False)
    assert result["credential_env_read_executed"] is False


def test_runner_not_executed(tmp_path: Path):
    result = run_prepare(tmp_path, create_ls6e_files=False)
    assert result["runner_executed"] is False

import json
import subprocess
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls6c_real_draft_payload_rebuild_dry_run_policy.json").read_text(encoding="utf-8"))


def valid_ls7a_result() -> dict:
    return {
        "status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED",
        "publish_decision": "DO_NOT_PUBLISH",
        "requires_payload_rebuild": True,
    }


def valid_ls7a_review() -> dict:
    return {
        "review_status": "DO_NOT_PUBLISH_SAMPLE_PAYLOAD",
        "manual_publish_allowed": False,
    }


def valid_not_ready_payload() -> dict:
    return {
        "status": "LS6C_REAL_INPUT_NOT_READY",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
    }


def valid_ready_payload() -> dict:
    return {
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "payload_ready": True,
        "max_items": 1,
        "payload_count": 1,
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
        "ls6b_rerun_executed": False,
        "payloads": [
            {
                "post_status": "draft",
                "content_format": "html",
                "content": "<p><a href=\"https://www.amazon.co.jp/dp/B0ABCDEF12?tag=yourtag-22\">Amazonで確認する</a></p>",
                "affiliate_disclosure_present": True,
                "affiliate_link_present": True,
                "html_link_present": True,
                "markdown_link_present": False,
                "category": "巻数ガイド",
                "tags": ["新刊"],
                "category_or_tag_present": True,
                "sample_content_detected": False,
            }
        ],
    }


def run_validator(tmp_path: Path, *, payload=None, policy=None, ls7a_result=None, ls7a_review=None) -> dict:
    p_policy = tmp_path / "policy.json"
    p_payload = tmp_path / "payload.json"
    p_ls7a_result = tmp_path / "ls7a_result.json"
    p_ls7a_review = tmp_path / "ls7a_review.json"
    p_output = tmp_path / "result.json"
    p_report = tmp_path / "report.md"

    write_json(p_policy, policy or valid_policy())
    write_json(p_payload, payload or valid_ready_payload())
    write_json(p_ls7a_result, ls7a_result or valid_ls7a_result())
    write_json(p_ls7a_review, ls7a_review or valid_ls7a_review())

    subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls6c_real_draft_payload_rebuild_dry_run.py",
            "--policy",
            str(p_policy),
            "--payload",
            str(p_payload),
            "--ls7a-result",
            str(p_ls7a_result),
            "--ls7a-review",
            str(p_ls7a_review),
            "--output",
            str(p_output),
            "--report",
            str(p_report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6C"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_not_ready_payload_recorded(tmp_path: Path):
    result = run_validator(tmp_path, payload=valid_not_ready_payload())
    assert result["status"] == "LS6C_REAL_INPUT_NOT_READY_RECORDED"


def test_ready_payload_validated(tmp_path: Path):
    result = run_validator(tmp_path, payload=valid_ready_payload())
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"


def test_ls7a_result_mismatch_not_ready(tmp_path: Path):
    bad = valid_ls7a_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, ls7a_result=bad)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_payload_count_gt1_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["payload_count"] = 2
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_post_status_not_draft_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_markdown_link_present_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["payloads"][0]["markdown_link_present"] = True
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_category_uncategorized_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["payloads"][0]["category"] = "未分類"
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_sample_content_detected_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["payloads"][0]["sample_content_detected"] = True
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"


def test_write_flag_true_not_ready(tmp_path: Path):
    payload = valid_ready_payload()
    payload["wordpress_write_executed"] = True
    result = run_validator(tmp_path, payload=payload)
    assert result["status"] == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"

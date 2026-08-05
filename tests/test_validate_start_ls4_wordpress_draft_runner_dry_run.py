import json
import subprocess
from pathlib import Path


def write_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls4_wordpress_draft_runner_dry_run_policy.json").read_text(encoding="utf-8"))


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
                "title": "Sample Volume 1 | Ebook Introduction",
                "content": "**PR** This page contains affiliate links.\n\nSample Volume 1\n\n[Check on Amazon](https://example.test/item)\n",
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


def run_validator(tmp_path: Path, payload: dict) -> dict:
    payload_path = tmp_path / "payload.json"
    output_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"
    write_payload(payload_path, payload)

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls4_wordpress_draft_runner_dry_run.py",
            "--payload",
            str(payload_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    result["_stdout"] = completed.stdout
    result["_report_path"] = str(report_path)
    return result


def test_policy_json_is_valid_and_flags_are_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-4"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"

    flags = policy["safety_flags"]
    assert flags["wordpress_api_call_allowed"] is False
    assert flags["wordpress_write_allowed"] is False
    assert flags["wordpress_draft_creation_executed"] is False
    assert flags["publish_allowed"] is False
    assert flags["publish_executed"] is False
    assert flags["future_schedule_allowed"] is False
    assert flags["future_schedule_executed"] is False
    assert flags["existing_post_update_allowed"] is False
    assert flags["existing_post_update_executed"] is False
    assert flags["delete_allowed"] is False
    assert flags["delete_executed"] is False
    assert flags["amazon_api_call_allowed"] is False
    assert flags["x_api_call_allowed"] is False
    assert flags["x_post_allowed"] is False
    assert flags["approval_token_consumed"] is False
    assert flags["phase_forward_execution_allowed"] is False


def test_valid_payload_ready(tmp_path):
    result = run_validator(tmp_path, valid_payload())
    assert result["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY"
    assert result["execution_mode"] == "DRY_RUN_ONLY"
    assert result["production_status"] == "NO_GO"
    assert result["wordpress_api_call_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_draft_creation_executed"] is False
    assert result["publish_executed"] is False
    assert result["max_items"] == 1
    assert result["payload_count"] == 1
    assert result["secret_values_output"] is False
    assert result["secret_lengths_output"] is False
    assert result["secret_hashes_output"] is False
    assert Path(result["_report_path"]).exists()
    assert "LS-4 WordPress Draft Runner DRY_RUN Report" in Path(result["_report_path"]).read_text(encoding="utf-8")


def test_non_draft_or_publish_executed_not_ready(tmp_path):
    payload = valid_payload()
    payload["payloads"][0]["post_status"] = "publish"
    result = run_validator(tmp_path, payload)
    assert result["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"

    payload2 = valid_payload()
    payload2["publish_executed"] = True
    result2 = run_validator(tmp_path, payload2)
    assert result2["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"


def test_payload_count_or_max_items_over_limit_not_ready(tmp_path):
    payload = valid_payload()
    payload["max_items"] = 2
    result = run_validator(tmp_path, payload)
    assert result["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"

    payload2 = valid_payload()
    payload2["payloads"].append(valid_payload()["payloads"][0])
    result2 = run_validator(tmp_path, payload2)
    assert result2["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"


def test_missing_affiliate_or_connection_refs_not_ready(tmp_path):
    payload = valid_payload()
    payload["payloads"][0]["affiliate_disclosure_present"] = False
    result = run_validator(tmp_path, payload)
    assert result["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"

    payload2 = valid_payload()
    del payload2["payloads"][0]["core_boundary_ref"]
    del payload2["payloads"][0]["audit_observation_ref"]
    del payload2["payloads"][0]["risk_score"]
    del payload2["payloads"][0]["rollback_pointer"]
    result2 = run_validator(tmp_path, payload2)
    assert result2["status"] == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"
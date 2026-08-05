"""Tests for run_phase8_9_first_one_item_wordpress_draft_create_rerun."""
import copy
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_phase8_9_first_one_item_wordpress_draft_create_rerun import run_first_one_item_draft_create_rerun  # noqa: E402


PHASE88_REL = "exchange/logs/phase8_8_final_credentialed_live_preflight_result.json"
REQUIRED_PHASE88_STATUS = "CREDENTIAL_PREFLIGHT_PASS_READY_FOR_PHASE8_9"


def base_policy():
    return {
        "phase": "Phase 8-9",
        "production_status": "LIMITED_DRAFT_CREATE_ONLY",
        "wordpress_draft_creation": "ALLOW_ONE_DRAFT_ONLY",
        "wordpress_api_call_allowed": True,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_execution": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "target_item_count": 1,
        "required_evidence": [PHASE88_REL],
        "required_phase8_8_status": REQUIRED_PHASE88_STATUS,
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "wordpress_request": {
            "method": "POST",
            "endpoint": "/wp-json/wp/v2/posts",
            "status": "draft",
            "max_posts": 1,
        },
        "retry_policy": {"retry_allowed": False, "max_retries": 0},
        "post_create_validation": {
            "require_post_id": True,
            "require_status_draft": True,
            "reject_status_publish": True,
            "require_link_or_guid": True,
        },
        "secret_output_policy": {
            "print_values": False,
            "write_values_to_logs": False,
            "print_lengths": False,
            "print_prefix_suffix": False,
            "hash_values": False,
        },
        "allowed_next_step": "Phase 8-10 post-rerun verification and controlled draft flow closure report",
    }


def base_request():
    return {
        "title": "テスト漫画 第1巻",
        "body": "PR：本記事には広告が含まれます。",
        "status": "draft",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    request: dict | None = None,
    phase88_status: str = REQUIRED_PHASE88_STATUS,
    missing_evidence: bool = False,
    mock_response: MagicMock | None = None,
    monkeypatch=None,
):
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    r = copy.deepcopy(request) if request is not None else base_request()

    policy_file = tmp_path / "policy.json"
    request_file = tmp_path / "request.json"
    policy_file.write_text(json.dumps(p), encoding="utf-8")
    request_file.write_text(json.dumps(r), encoding="utf-8")

    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)

    if not missing_evidence:
        (ev_dir / "phase8_8_final_credentialed_live_preflight_result.json").write_text(
            json.dumps({"status": phase88_status}), encoding="utf-8"
        )
        p["required_evidence"] = [
            str(ev_dir / "phase8_8_final_credentialed_live_preflight_result.json")
        ]
        policy_file.write_text(json.dumps(p), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    if mock_response is not None and monkeypatch is not None:
        monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
        monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
        monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "abcd efgh ijkl mnop")
        with patch(
            "run_phase8_9_first_one_item_wordpress_draft_create_rerun.requests.post",
            return_value=mock_response,
        ):
            return run_first_one_item_draft_create_rerun(policy_file, request_file, out_json, out_md)
    return run_first_one_item_draft_create_rerun(policy_file, request_file, out_json, out_md)


def test_not_executed_credential_preflight_not_ready_on_wrong_phase88_status(tmp_path):
    result = run_case(tmp_path, phase88_status="NOT_READY_CREDENTIALS_MISSING")
    assert result["status"] == "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY"
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_executed"] is False


def test_not_executed_credential_preflight_not_ready_on_missing_evidence(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY"
    assert result["wordpress_api_call_attempted"] is False


def test_credentials_missing_not_executed(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("WORDPRESS_APP_PASSWORD", raising=False)
    result = run_case(tmp_path)
    assert result["status"] == "RERUN_NOT_EXECUTED_MISSING_CREDENTIALS"
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_executed"] is False


def test_draft_created_on_201(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": 42,
        "status": "draft",
        "link": "https://example.com/wp-admin/post.php?post=42",
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert result["post_id"] == 42
    assert result["post_status"] == "draft"
    assert result["wordpress_write_executed"] is True
    assert result["secret_values_written"] is False


def test_draft_created_on_200(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": 55,
        "status": "draft",
        "link": "https://example.com/wp-admin/post.php?post=55",
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert result["post_id"] == 55


def test_abort_on_publish_status_in_response(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": 99,
        "status": "publish",
        "link": "https://example.com/?p=99",
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "ABORT"
    assert result["wordpress_write_executed"] is False


def test_failed_on_missing_id(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "status": "draft",
        "link": "https://example.com/wp-admin/post.php?post=0",
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
    assert result["wordpress_write_executed"] is False


def test_failed_on_missing_link(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": 123, "status": "draft"}
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"


def test_failed_on_5xx(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = {}
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"


def test_failed_on_requests_exception(tmp_path, monkeypatch):
    import requests as req_mod
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "abcd efgh ijkl mnop")

    policy_file = tmp_path / "policy.json"
    request_file = tmp_path / "request.json"
    pol = base_policy()
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_8_final_credentialed_live_preflight_result.json").write_text(
        json.dumps({"status": REQUIRED_PHASE88_STATUS}), encoding="utf-8"
    )
    pol["required_evidence"] = [str(ev_dir / "phase8_8_final_credentialed_live_preflight_result.json")]
    policy_file.write_text(json.dumps(pol), encoding="utf-8")
    request_file.write_text(json.dumps(base_request()), encoding="utf-8")

    with patch(
        "run_phase8_9_first_one_item_wordpress_draft_create_rerun.requests.post",
        side_effect=req_mod.RequestException("connection error"),
    ):
        result = run_first_one_item_draft_create_rerun(
            policy_file, request_file, tmp_path / "out.json", tmp_path / "out.md"
        )
    assert result["status"] == "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"


def test_abort_publish_allowed_true(tmp_path):
    pol = base_policy()
    pol["publish_allowed"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_secret_output_policy_print_values_true(tmp_path):
    pol = base_policy()
    pol["secret_output_policy"]["print_values"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_target_item_count_not_1(tmp_path):
    pol = base_policy()
    pol["target_item_count"] = 2
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_max_posts_not_1(tmp_path):
    pol = base_policy()
    pol["wordpress_request"]["max_posts"] = 2
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_request_status_not_draft(tmp_path):
    pol = base_policy()
    pol["wordpress_request"]["status"] = "publish"
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_secret_values_never_in_output(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": 77,
        "status": "draft",
        "link": "https://example.com/?p=77",
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    result_str = json.dumps(result)
    assert "ai_publisher" not in result_str
    assert "abcd efgh ijkl mnop" not in result_str


def test_guid_used_when_link_absent(tmp_path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": 88,
        "status": "draft",
        "guid": {"rendered": "https://example.com/?p=88"},
    }
    result = run_case(tmp_path, mock_response=mock_resp, monkeypatch=monkeypatch)
    assert result["status"] == "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert result["post_link"] == "https://example.com/?p=88"

"""Tests for validate_phase8_8_final_credentialed_live_preflight."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_8_final_credentialed_live_preflight import validate_final_credentialed_live_preflight  # noqa: E402


PHASE82_REL = "exchange/logs/phase8_2_final_live_preflight_result.json"
PHASE86_REL = "exchange/logs/phase8_6_wordpress_credentials_readiness_result.json"
PHASE87_REL = "exchange/logs/phase8_7_rerun_approval_review_result.json"


def base_policy():
    return {
        "phase": "Phase 8-8",
        "production_status": "NO_GO",
        "preflight_is_execution_permission": False,
        "phase8_9_may_execute_if_this_passes": True,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_evidence": [PHASE82_REL, PHASE86_REL, PHASE87_REL],
        "required_statuses": {
            "phase8_2": "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE",
            "phase8_7": "PASS_RERUN_REVIEW_ONLY",
        },
        "required_credential_status": "CREDENTIALS_READY_NO_SECRET_OUTPUT",
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step": "Phase 8-9 first one-item WordPress draft creation rerun, only if all gates pass",
    }


def base_request():
    return {
        "phase": "Phase 8-8",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "candidate_id": "test_candidate_001",
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "title": "テスト投稿",
        "body": "PR：本記事には広告が含まれます。",
        "category": "電子書籍",
        "affiliate_links": [
            {"store": "amazon", "url": "https://example.com/affiliate/sample"}
        ],
        "cta": [
            {"label": "Amazonで見る", "url": "https://example.com/affiliate/sample"}
        ],
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "publish_allowed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    request: dict | None = None,
    phase82_status: str = "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE",
    phase86_status: str = "CREDENTIALS_READY_NO_SECRET_OUTPUT",
    phase87_status: str = "PASS_RERUN_REVIEW_ONLY",
    missing_evidence: bool = False,
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
        (ev_dir / "phase8_2_final_live_preflight_result.json").write_text(
            json.dumps({"status": phase82_status}), encoding="utf-8"
        )
        (ev_dir / "phase8_6_wordpress_credentials_readiness_result.json").write_text(
            json.dumps({"status": phase86_status}), encoding="utf-8"
        )
        (ev_dir / "phase8_7_rerun_approval_review_result.json").write_text(
            json.dumps({"status": phase87_status}), encoding="utf-8"
        )
        p["required_evidence"] = [
            str(ev_dir / "phase8_2_final_live_preflight_result.json"),
            str(ev_dir / "phase8_6_wordpress_credentials_readiness_result.json"),
            str(ev_dir / "phase8_7_rerun_approval_review_result.json"),
        ]
        policy_file.write_text(json.dumps(p), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    return validate_final_credentialed_live_preflight(policy_file, request_file, out_json, out_md)


def test_credentials_ready_pass(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIAL_PREFLIGHT_PASS_READY_FOR_PHASE8_9"


def test_credentials_not_ready(tmp_path):
    result = run_case(tmp_path, phase86_status="CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "NOT_READY_CREDENTIALS_MISSING"


def test_abort_missing_evidence(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_abort_phase82_wrong_status(tmp_path):
    result = run_case(tmp_path, phase82_status="WRONG")
    assert result["status"] == "ABORT"


def test_abort_phase87_wrong_status(tmp_path):
    result = run_case(tmp_path, phase87_status="WRONG")
    assert result["status"] == "ABORT"


def test_abort_phase86_invalid_status(tmp_path):
    result = run_case(tmp_path, phase86_status="INVALID_STATUS")
    assert result["status"] == "ABORT"


def test_abort_preflight_is_execution_permission_true(tmp_path):
    pol = base_policy()
    pol["preflight_is_execution_permission"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_wordpress_api_call_allowed_true(tmp_path):
    pol = base_policy()
    pol["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_publish_allowed_true(tmp_path):
    pol = base_policy()
    pol["publish_allowed"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_safety_flags_auto_post_true(tmp_path):
    req = base_request()
    req["safety_flags"]["auto_post"] = True
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_abort_http_affiliate_url(tmp_path):
    req = base_request()
    req["affiliate_links"] = [{"store": "amazon", "url": "http://example.com/affiliate"}]
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_abort_javascript_cta_url(tmp_path):
    req = base_request()
    req["cta"] = [{"label": "click", "url": "javascript:void(0)"}]
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_fail_missing_pr_notation_in_body(tmp_path):
    req = base_request()
    req["body"] = "この漫画はセールです。"
    result = run_case(tmp_path, request=req)
    assert result["status"] == "FAIL"


def test_abort_wrong_approval_token(tmp_path):
    req = base_request()
    req["approval_token"] = "WRONG"
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_abort_target_item_count_not_1(tmp_path):
    req = base_request()
    req["target_item_count"] = 2
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["preflight_is_execution_permission"] is False
    assert result["phase8_9_may_execute_if_this_passes"] is True

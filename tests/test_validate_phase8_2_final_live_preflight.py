import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_2_final_live_preflight import validate_final_live_preflight


def base_policy() -> dict:
    return {
        "phase": "Phase 8-2",
        "name": "final_live_preflight_policy",
        "policy_status": "PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "preflight_is_execution_permission": False,
        "phase8_3_may_execute_if_this_passes": True,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_allowed_in_phase8_2": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase7_14_pre_live_unlock_final_report.json",
            "exchange/logs/phase8_1_explicit_human_approval_result.json",
        ],
        "required_statuses": {
            "phase7_14": "READY_FOR_PHASE8_HUMAN_APPROVAL_BUT_NO_GO",
            "phase8_1": "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY",
        },
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_write_executed": False,
            "wordpress_api_call_allowed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def base_request() -> dict:
    return {
        "phase": "Phase 8-2",
        "source": "FINAL_LIVE_PREFLIGHT_WITH_EXPLICIT_APPROVAL",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "title": "サンプル漫画 1巻 セール紹介",
        "body": "PR：本記事には広告が含まれます。これは preflight 本文です。",
        "category": "電子書籍",
        "tags": ["漫画", "セール", "電子書籍"],
        "affiliate_links": [{"store": "amazon", "url": "https://example.com/affiliate/sample"}],
        "cta": [{"label": "Amazonで見る", "url": "https://example.com/affiliate/sample"}],
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "wordpress_api_call_allowed": False,
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


def run_case(tmp_path: Path, policy=None, request=None, missing_evidence=False, phase714="READY_FOR_PHASE8_HUMAN_APPROVAL_BUT_NO_GO", phase81="APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY"):
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(request or base_request())

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)

    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    if not missing_evidence:
        ev1 = tmp_path / p["required_evidence"][0]
        ev2 = tmp_path / p["required_evidence"][1]
        ev1.parent.mkdir(parents=True, exist_ok=True)
        ev2.parent.mkdir(parents=True, exist_ok=True)
        ev1.write_text(json.dumps({"status": phase714}), encoding="utf-8")
        ev2.write_text(json.dumps({"status": phase81}), encoding="utf-8")

    return validate_final_live_preflight(policy_path, request_path, out_json, out_md)


def test_normal_pass(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE"


def test_evidence_missing_abort(tmp_path: Path):
    assert run_case(tmp_path, missing_evidence=True)["status"] == "ABORT"


def test_phase81_wrong_status_abort(tmp_path: Path):
    assert run_case(tmp_path, phase81="FAIL")["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    r = base_request()
    r["target_item_count"] = 2
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_approval_token_wrong_abort(tmp_path: Path):
    r = base_request()
    r["approval_token"] = "WRONG"
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_missing_pr_fail(tmp_path: Path):
    r = base_request()
    r["body"] = "これは注記なし本文です。"
    assert run_case(tmp_path, request=r)["status"] == "FAIL"


def test_empty_body_fail(tmp_path: Path):
    r = base_request()
    r["body"] = ""
    assert run_case(tmp_path, request=r)["status"] == "FAIL"


def test_affiliate_http_abort(tmp_path: Path):
    r = base_request()
    r["affiliate_links"][0]["url"] = "http://example.com/affiliate/sample"
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_affiliate_javascript_abort(tmp_path: Path):
    r = base_request()
    r["affiliate_links"][0]["url"] = "javascript:alert(1)"
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_api_allowed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_write_executed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["wordpress_write_executed"] = True
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["publish_allowed"] = True
    assert run_case(tmp_path, request=r)["status"] == "ABORT"


def test_preflight_permission_true_abort(tmp_path: Path):
    p = base_policy()
    p["preflight_is_execution_permission"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_auto_post_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["auto_post"] = True
    assert run_case(tmp_path, request=r)["status"] == "ABORT"

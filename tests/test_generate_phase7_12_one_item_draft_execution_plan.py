import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase7_12_one_item_draft_execution_plan import generate_plan


def base_policy() -> dict:
    return {
        "phase": "Phase 7-12",
        "name": "one_item_draft_execution_plan_policy",
        "policy_status": "DRY_RUN_PLAN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "execution_plan_is_execution_permission": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": ["exchange/logs/phase7_11_approve_draft_create_only_token_validation_result.json"],
        "required_phase7_11_status": "TOKEN_READY_BUT_LOCKED",
        "plan_generation_allowed": True,
        "payload_generation_allowed": True,
        "payload_write_allowed": False,
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


def base_input() -> dict:
    return {
        "phase": "Phase 7-12",
        "source": "ONE_ITEM_DRAFT_EXECUTION_PLAN_DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "title": "サンプル漫画 1巻 セール紹介",
        "body": "PR：本記事には広告が含まれます。これはPhase 7-12の実行計画DRY_RUN用本文です。WordPress APIは呼びません。",
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


def run_case(tmp_path: Path, policy=None, inp=None, evidence_status="TOKEN_READY_BUT_LOCKED", missing=False) -> dict:
    p = copy.deepcopy(policy or base_policy())
    i = copy.deepcopy(inp or base_input())
    policy_path = tmp_path / "config/policy.json"
    in_path = tmp_path / "exchange/examples/input.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    in_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    in_path.write_text(json.dumps(i, ensure_ascii=False, indent=2), encoding="utf-8")
    if not missing:
        e = tmp_path / p["required_evidence"][0]
        e.parent.mkdir(parents=True, exist_ok=True)
        e.write_text(json.dumps({"status": evidence_status}), encoding="utf-8")
    return generate_plan(policy_path, in_path, out_json, out_md)


def test_normal_ready_no_go(tmp_path: Path):
    r = run_case(tmp_path)
    assert r["status"] == "EXECUTION_PLAN_READY_BUT_NO_GO"
    assert r["planned_wordpress_payload"]["status"] == "draft_candidate_plan_only"


def test_evidence_missing_fail(tmp_path: Path):
    assert run_case(tmp_path, missing=True)["status"] == "FAIL"


def test_evidence_abort_abort(tmp_path: Path):
    assert run_case(tmp_path, evidence_status="ABORT")["status"] == "ABORT"


def test_execution_permission_true_abort(tmp_path: Path):
    p = base_policy()
    p["execution_plan_is_execution_permission"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_policy_approve_enabled_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_unlock_true_abort(tmp_path: Path):
    p = base_policy()
    p["unlock_in_this_phase"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_api_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_payload_write_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["payload_write_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_write_executed_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["publish_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    i = base_input()
    i["target_item_count"] = 2
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_affiliate_http_abort(tmp_path: Path):
    i = base_input()
    i["affiliate_links"][0]["url"] = "http://example.com/affiliate/sample"
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_missing_pr_fail(tmp_path: Path):
    i = base_input()
    i["body"] = "これは注記なし本文です。"
    assert run_case(tmp_path, inp=i)["status"] == "FAIL"


def test_empty_body_fail(tmp_path: Path):
    i = base_input()
    i["body"] = ""
    assert run_case(tmp_path, inp=i)["status"] == "FAIL"


def test_auto_post_true_abort(tmp_path: Path):
    i = base_input()
    i["safety_flags"]["auto_post"] = True
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_phase7_8_single_draft_create_simulation import run_simulation


def base_policy() -> dict:
    return {
        "phase": "Phase 7-8",
        "name": "single_draft_create_simulation_policy",
        "policy_status": "DRY_RUN_SIMULATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "simulation_only": True,
        "wordpress_api_call_allowed": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase7_7_approve_draft_create_only_readiness_gate_result.json"
        ],
        "required_readiness_status": "READY_BUT_LOCKED",
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
        "phase": "Phase 7-8",
        "source": "SINGLE_DRAFT_CREATE_SIMULATION",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "title": "サンプル漫画 1巻 セール紹介",
        "body": "PR：本記事には広告が含まれます。シミュレーション本文です。",
        "category": "電子書籍",
        "tags": ["漫画"],
        "affiliate_links": [{"store": "amazon", "url": "https://example.com/a"}],
        "cta": [{"label": "Amazonで見る", "url": "https://example.com/a"}],
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "publish_allowed": False,
            "wordpress_api_call_allowed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def run_case(tmp_path: Path, policy: dict | None = None, inp: dict | None = None, readiness: str | None = "READY_BUT_LOCKED") -> dict:
    p = copy.deepcopy(policy or base_policy())
    i = copy.deepcopy(inp or base_input())
    policy_path = tmp_path / "config/policy.json"
    input_path = tmp_path / "exchange/examples/input.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    input_path.write_text(json.dumps(i, ensure_ascii=False, indent=2), encoding="utf-8")
    if readiness is not None:
        e = tmp_path / p["required_evidence"][0]
        e.parent.mkdir(parents=True, exist_ok=True)
        e.write_text(json.dumps({"status": readiness}), encoding="utf-8")
    return run_simulation(policy_path, input_path, out_json, out_md)


def test_normal_simulation_pass(tmp_path: Path):
    r = run_case(tmp_path)
    assert r["status"] == "SIMULATION_PASS_DRY_RUN_ONLY"
    assert r["simulated_wordpress_payload"]["status"] == "draft_candidate_simulation_only"


def test_readiness_missing_not_ready(tmp_path: Path):
    assert run_case(tmp_path, readiness=None)["status"] == "NOT_READY"


def test_readiness_abort_abort(tmp_path: Path):
    assert run_case(tmp_path, readiness="ABORT")["status"] == "ABORT"


def test_wordpress_api_call_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_payload_write_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["payload_write_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_wordpress_write_executed_true_abort(tmp_path: Path):
    i = base_input()
    i["safety_flags"]["wordpress_write_executed"] = True
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    i = base_input()
    i["safety_flags"]["publish_allowed"] = True
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_target_item_count_two_abort(tmp_path: Path):
    i = base_input()
    i["target_item_count"] = 2
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_affiliate_http_abort(tmp_path: Path):
    i = base_input()
    i["affiliate_links"][0]["url"] = "http://example.com/a"
    assert run_case(tmp_path, inp=i)["status"] == "ABORT"


def test_missing_pr_notation_fail(tmp_path: Path):
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

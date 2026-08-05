import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_1_eligible_single_controlled_run_policy import validate_policy


def base_policy() -> dict:
    return {
        "phase": "Phase 7-1",
        "name": "eligible_single_controlled_run_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "eligible_is_execution_permission": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "future_reserved_decision_token": {
            "token": "APPROVE_DRAFT_CREATE_ONLY",
            "currently_allowed": False,
            "phase7_1_allows_this_token": False,
            "meaning": "reserved",
        },
        "single_item_limit": {
            "enabled": True,
            "required": True,
            "max_items": 1,
            "bulk_run_allowed": False,
        },
        "required_phase6_evidence": [
            "exchange/logs/phase6_5_execution_spec_validation_result.json",
            "exchange/logs/phase6_6_quality_gate_validation_result.json",
            "exchange/logs/phase6_7_slack_approval_dry_run_result.json",
            "exchange/logs/phase6_8_runbook_validation_result.json",
            "exchange/logs/phase6_9_hardening_preflight_report.json",
            "exchange/logs/phase6_10_existing_generated_test_fix_report.json",
        ],
        "acceptable_phase6_statuses": [
            "PASS",
            "PASS_DRY_RUN_ONLY",
            "PASS_DRY_RUN_ONLY_WITH_WARN",
        ],
        "candidate_required_fields": [
            "candidate_id",
            "source",
            "target_item_count",
            "duplicate_check",
            "quality_gate",
            "pr_notice",
            "cta",
            "affiliate_links",
            "human_review",
            "freeze_plan",
            "safety_flags",
        ],
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_write_executed": False,
            "wordpress_rest_api_post": False,
            "wordpress_rest_api_put": False,
            "wordpress_rest_api_patch": False,
            "wordpress_rest_api_delete": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step": "Phase 7-2 APPROVE_DRAFT_CREATE_ONLY pre-unlock review design only",
        "blocked_next_steps": ["wordpress_draft_create"],
    }


def base_candidate() -> dict:
    return {
        "candidate_id": "sample-001",
        "source": "PHASE7_1_ELIGIBLE_DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "decision_token": "ELIGIBLE",
        "duplicate_check": {"status": "PASS"},
        "quality_gate": {"status": "PASS_DRY_RUN_ONLY"},
        "pr_notice": {"exists": True, "text": "PR"},
        "cta": {
            "exists": True,
            "items": [{"label": "Amazon", "url": "https://example.com/cta"}],
        },
        "affiliate_links": [{"store": "amazon", "url": "https://example.com/link"}],
        "human_review": {
            "required": True,
            "status": "REQUIRED_NOT_APPROVED_IN_PHASE7_1",
            "approval_token_used": False,
            "approve_draft_create_only_used": False,
        },
        "freeze_plan": {
            "exists": True,
            "freeze_on_mismatch": True,
            "freeze_on_wordpress_write_attempt": True,
            "freeze_on_bulk_execution": True,
        },
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def write_fixture_tree(tmp_path: Path, policy: dict, candidate: dict, evidence_statuses: list[str] | None = None) -> tuple[Path, Path, Path, Path]:
    config_dir = tmp_path / "config"
    examples_dir = tmp_path / "exchange/examples"
    logs_dir = tmp_path / "exchange/logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    examples_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    policy_path = config_dir / "phase7_1_eligible_single_controlled_run_policy.json"
    candidate_path = examples_dir / "phase7_1_eligible_candidate.example.json"
    out_json = logs_dir / "phase7_1_eligible_single_controlled_run_policy_result.json"
    out_md = logs_dir / "phase7_1_eligible_single_controlled_run_policy_result.md"

    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")

    statuses = evidence_statuses or [
        "PASS_DRY_RUN_ONLY",
        "PASS_DRY_RUN_ONLY",
        "PASS_DRY_RUN_ONLY",
        "PASS_DRY_RUN_ONLY",
        "PASS_DRY_RUN_ONLY",
        "PASS",
    ]
    evidence_files = policy["required_phase6_evidence"]
    for idx, rel in enumerate(evidence_files):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        status = statuses[idx]
        payload = {"phase": f"phase-{idx+1}"}
        if "phase6_9" in rel:
            payload["overall_status"] = status
        else:
            payload["status"] = status
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return policy_path, candidate_path, out_json, out_md


def run_case(tmp_path: Path, policy: dict | None = None, candidate: dict | None = None, evidence_statuses: list[str] | None = None) -> dict:
    pol = copy.deepcopy(policy or base_policy())
    cand = copy.deepcopy(candidate or base_candidate())
    policy_path, candidate_path, out_json, out_md = write_fixture_tree(tmp_path, pol, cand, evidence_statuses)
    return validate_policy(policy_path, candidate_path, out_json, out_md)


def test_normal_case_eligible_dry_run_only(tmp_path: Path):
    result = run_case(tmp_path)
    assert result["status"] == "ELIGIBLE_DRY_RUN_ONLY"


def test_policy_production_status_go_aborts(tmp_path: Path):
    policy = base_policy()
    policy["production_status"] = "GO"
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_policy_execution_live_aborts(tmp_path: Path):
    policy = base_policy()
    policy["execution"] = "LIVE"
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_policy_wordpress_write_executed_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["wordpress_write_executed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_policy_publish_allowed_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["publish_allowed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_reserved_token_currently_allowed_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["future_reserved_decision_token"]["currently_allowed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_phase7_1_allows_reserved_token_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["future_reserved_decision_token"]["phase7_1_allows_this_token"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_single_item_limit_two_aborts(tmp_path: Path):
    policy = base_policy()
    policy["single_item_limit"]["max_items"] = 2
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_candidate_target_item_count_two_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["target_item_count"] = 2
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_candidate_decision_token_reserved_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["decision_token"] = "APPROVE_DRAFT_CREATE_ONLY"
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_duplicate_check_fail_not_eligible(tmp_path: Path):
    candidate = base_candidate()
    candidate["duplicate_check"]["status"] = "FAIL"
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "NOT_ELIGIBLE"


def test_quality_gate_fail_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["quality_gate"]["status"] = "FAIL"
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_pr_notice_missing_not_eligible(tmp_path: Path):
    candidate = base_candidate()
    candidate["pr_notice"]["exists"] = False
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "NOT_ELIGIBLE"


def test_cta_missing_not_eligible(tmp_path: Path):
    candidate = base_candidate()
    candidate["cta"]["exists"] = False
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "NOT_ELIGIBLE"


def test_affiliate_links_empty_not_eligible(tmp_path: Path):
    candidate = base_candidate()
    candidate["affiliate_links"] = []
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "NOT_ELIGIBLE"


def test_affiliate_link_http_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["affiliate_links"][0]["url"] = "http://example.com/link"
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_affiliate_link_javascript_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["affiliate_links"][0]["url"] = "javascript:alert(1)"
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_human_review_required_false_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["human_review"]["required"] = False
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_human_review_approve_token_used_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["human_review"]["approve_draft_create_only_used"] = True
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_freeze_plan_exists_false_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["freeze_plan"]["exists"] = False
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_safety_flags_auto_post_true_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["safety_flags"]["auto_post"] = True
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_safety_flags_wordpress_write_executed_true_aborts(tmp_path: Path):
    candidate = base_candidate()
    candidate["safety_flags"]["wordpress_write_executed"] = True
    result = run_case(tmp_path, candidate=candidate)
    assert result["status"] == "ABORT"


def test_phase6_evidence_missing_aborts(tmp_path: Path):
    policy = base_policy()
    candidate = base_candidate()
    policy_path, candidate_path, out_json, out_md = write_fixture_tree(tmp_path, policy, candidate)
    missing_path = tmp_path / policy["required_phase6_evidence"][0]
    missing_path.unlink()
    result = validate_policy(policy_path, candidate_path, out_json, out_md)
    assert result["status"] == "ABORT"


def test_phase6_evidence_status_abort_aborts(tmp_path: Path):
    result = run_case(
        tmp_path,
        evidence_statuses=["ABORT", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS"],
    )
    assert result["status"] == "ABORT"


def test_phase6_evidence_status_fail_aborts(tmp_path: Path):
    result = run_case(
        tmp_path,
        evidence_statuses=["FAIL", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS"],
    )
    assert result["status"] == "ABORT"

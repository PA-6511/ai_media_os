import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_auto_builder_token_budget_and_snapshot_digest import (  # noqa: E402
    validate_all,
)


def base_budget_policy() -> dict:
    return {
        "phase": "AB-T0.5",
        "name": "Token Budget Governor",
        "status": "DESIGN_ONLY",
        "final_status": "PASS_DESIGN_ONLY_NO_EXECUTION",
        "production_status": "NO_GO",
        "execution_status": "NO_EXECUTION",
        "dry_run_only": True,
        "evidence_only": True,
        "external_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "production_write_allowed": False,
        "credential_read_allowed": False,
        "credential_output_allowed": False,
        "secret_reading_allowed": False,
        "secret_printing_allowed": False,
        "live_execution_allowed": False,
        "copilot_agent_default_allowed": False,
        "copilot_agent_allowed_without_human_override": False,
        "max_files_per_ai_context": 5,
        "max_lines_per_file_excerpt": 120,
        "max_ai_context_items_per_turn": 8,
        "max_git_diff_lines_for_ai": 0,
        "full_repository_dump_allowed": False,
        "git_diff_full_paste_allowed": False,
        "pytest_full_log_paste_allowed": False,
        "py_compile_full_log_paste_allowed": False,
        "json_tool_full_log_paste_allowed": False,
        "evidence_index_full_paste_allowed": False,
        "report_full_regeneration_allowed": False,
        "allowed_context_artifacts": [
            "phase_closure_card",
            "repository_snapshot_digest",
            "file_manifest",
            "diff_digest",
            "error_only_log",
            "safety_rule_pack",
        ],
        "forbidden_context_artifacts": [
            "full_repository_dump",
            "full_git_diff",
            "full_pytest_log",
            "full_evidence_index",
            "credential_files",
            "secrets_directory",
            "unrelated_historical_phase_reports",
        ],
        "safety_rule_pack_id": "SAFETY_RULE_PACK_AB_V1",
        "next_allowed_action": "Phase 1N-FIX pre-live resnapshot evidence cleanup only",
    }


def base_snapshot_digest() -> dict:
    return {
        "phase": "AB-T1",
        "name": "Repository Snapshot Digest LIGHTWEIGHT",
        "status": "DESIGN_ONLY",
        "final_status": "PASS_LIGHTWEIGHT_DESIGN_ONLY_NO_EXECUTION",
        "repository": "ai_media_os",
        "current_state": {
            "phase_1m_fix": "PASS",
            "phase_1n": "PASS",
            "ab_t0": "PASS_DESIGN_ONLY_NO_EXECUTION",
            "ab_t05": "PASS_DESIGN_ONLY_NO_EXECUTION",
            "next_phase": "Phase 1N-FIX pre-live resnapshot evidence cleanup",
            "phase_1_5_goal": "close readiness",
        },
        "safety": {
            "production_status": "NO_GO",
            "execution_status": "NO_EXECUTION",
            "dry_run_only": True,
            "evidence_only": True,
            "live_execution_allowed": False,
            "production_write_allowed": False,
            "wordpress_write_allowed": False,
            "external_api_call_allowed": False,
            "credential_read_allowed": False,
            "credential_output_allowed": False,
        },
        "token_efficiency": {
            "max_files_per_ai_context": 5,
            "max_lines_per_file_excerpt": 120,
            "copilot_agent_default_allowed": False,
            "full_diff_allowed": False,
            "full_log_allowed": False,
            "full_evidence_index_allowed": False,
            "repository_snapshot_digest_required": True,
        },
        "allowed_next_action": "Phase 1N-FIX evidence/report/snapshot cleanup only",
        "forbidden_actions": [
            "live_execution",
            "production_write",
            "wordpress_write",
            "external_api_call",
            "credential_read",
            "credential_output",
            "broad_refactor",
            "phase8_body_change",
        ],
    }


def write_inputs(tmp_path: Path, policy: dict, digest: dict) -> tuple[Path, Path]:
    policy_path = tmp_path / "config/auto_builder_token_budget_governor_policy.json"
    digest_path = tmp_path / "config/repository_snapshot_digest.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    digest_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return policy_path, digest_path


def run_case(tmp_path: Path, policy: dict | None = None, digest: dict | None = None) -> dict:
    p = copy.deepcopy(policy or base_budget_policy())
    d = copy.deepcopy(digest or base_snapshot_digest())
    policy_path, digest_path = write_inputs(tmp_path, p, d)
    return validate_all(policy_path, digest_path)


def test_normal_policy_and_snapshot_pass(tmp_path: Path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS"


def test_fails_when_production_status_go(tmp_path: Path):
    policy = base_budget_policy()
    policy["production_status"] = "GO"
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_execution_status_executed(tmp_path: Path):
    policy = base_budget_policy()
    policy["execution_status"] = "EXECUTED"
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_dry_run_only_false(tmp_path: Path):
    policy = base_budget_policy()
    policy["dry_run_only"] = False
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_production_write_allowed_true(tmp_path: Path):
    policy = base_budget_policy()
    policy["production_write_allowed"] = True
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_credential_output_allowed_true(tmp_path: Path):
    policy = base_budget_policy()
    policy["credential_output_allowed"] = True
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_copilot_agent_default_allowed_true(tmp_path: Path):
    policy = base_budget_policy()
    policy["copilot_agent_default_allowed"] = True
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_max_files_per_ai_context_over_5(tmp_path: Path):
    policy = base_budget_policy()
    policy["max_files_per_ai_context"] = 6
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_git_diff_full_paste_allowed_true(tmp_path: Path):
    policy = base_budget_policy()
    policy["git_diff_full_paste_allowed"] = True
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_safety_rule_pack_id_mismatch(tmp_path: Path):
    policy = base_budget_policy()
    policy["safety_rule_pack_id"] = "SAFETY_RULE_PACK_AB_V2"
    with pytest.raises(ValueError):
        run_case(tmp_path, policy=policy)


def test_fails_when_snapshot_phase_1n_not_pass(tmp_path: Path):
    digest = base_snapshot_digest()
    digest["current_state"]["phase_1n"] = "FAIL"
    with pytest.raises(ValueError):
        run_case(tmp_path, digest=digest)


def test_fails_when_snapshot_full_diff_allowed_true(tmp_path: Path):
    digest = base_snapshot_digest()
    digest["token_efficiency"]["full_diff_allowed"] = True
    with pytest.raises(ValueError):
        run_case(tmp_path, digest=digest)

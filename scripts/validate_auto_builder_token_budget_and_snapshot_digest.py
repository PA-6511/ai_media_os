#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUDGET_POLICY = ROOT / "config/auto_builder_token_budget_governor_policy.json"
DEFAULT_SNAPSHOT_DIGEST = ROOT / "config/repository_snapshot_digest.json"

REQUIRED_BUDGET_KEYS = {
    "phase",
    "name",
    "status",
    "final_status",
    "production_status",
    "execution_status",
    "dry_run_only",
    "evidence_only",
    "external_api_call_allowed",
    "wordpress_write_allowed",
    "production_write_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
    "secret_reading_allowed",
    "secret_printing_allowed",
    "live_execution_allowed",
    "copilot_agent_default_allowed",
    "copilot_agent_allowed_without_human_override",
    "max_files_per_ai_context",
    "max_lines_per_file_excerpt",
    "max_ai_context_items_per_turn",
    "max_git_diff_lines_for_ai",
    "full_repository_dump_allowed",
    "git_diff_full_paste_allowed",
    "pytest_full_log_paste_allowed",
    "py_compile_full_log_paste_allowed",
    "json_tool_full_log_paste_allowed",
    "evidence_index_full_paste_allowed",
    "report_full_regeneration_allowed",
    "allowed_context_artifacts",
    "forbidden_context_artifacts",
    "safety_rule_pack_id",
    "next_allowed_action",
}

REQUIRED_BUDGET_FALSE_FLAGS = [
    "external_api_call_allowed",
    "wordpress_write_allowed",
    "production_write_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
    "secret_reading_allowed",
    "secret_printing_allowed",
    "live_execution_allowed",
    "copilot_agent_default_allowed",
    "copilot_agent_allowed_without_human_override",
    "full_repository_dump_allowed",
    "git_diff_full_paste_allowed",
    "pytest_full_log_paste_allowed",
    "py_compile_full_log_paste_allowed",
    "json_tool_full_log_paste_allowed",
    "evidence_index_full_paste_allowed",
    "report_full_regeneration_allowed",
]

REQUIRED_SNAPSHOT_TOP_KEYS = {
    "phase",
    "name",
    "status",
    "final_status",
    "repository",
    "current_state",
    "safety",
    "token_efficiency",
    "allowed_next_action",
    "forbidden_actions",
}

REQUIRED_CURRENT_STATE_KEYS = {
    "phase_1m_fix",
    "phase_1n",
    "ab_t0",
    "ab_t05",
    "next_phase",
    "phase_1_5_goal",
}

REQUIRED_SAFETY_KEYS = {
    "production_status",
    "execution_status",
    "dry_run_only",
    "evidence_only",
    "live_execution_allowed",
    "production_write_allowed",
    "wordpress_write_allowed",
    "external_api_call_allowed",
    "credential_read_allowed",
    "credential_output_allowed",
}

REQUIRED_TOKEN_EFFICIENCY_KEYS = {
    "max_files_per_ai_context",
    "max_lines_per_file_excerpt",
    "copilot_agent_default_allowed",
    "full_diff_allowed",
    "full_log_allowed",
    "full_evidence_index_allowed",
    "repository_snapshot_digest_required",
}


class ValidationError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_keys(payload: dict[str, Any], required: set[str], scope: str) -> None:
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValidationError(f"{scope} missing required keys: {missing}")


def validate_token_budget_policy_data(policy: dict[str, Any]) -> dict[str, Any]:
    _require_keys(policy, REQUIRED_BUDGET_KEYS, "budget_policy")

    if policy.get("phase") != "AB-T0.5":
        raise ValidationError("budget_policy.phase must be AB-T0.5")
    if policy.get("production_status") != "NO_GO":
        raise ValidationError("budget_policy.production_status must be NO_GO")
    if policy.get("execution_status") != "NO_EXECUTION":
        raise ValidationError("budget_policy.execution_status must be NO_EXECUTION")
    if policy.get("dry_run_only") is not True:
        raise ValidationError("budget_policy.dry_run_only must be true")
    if policy.get("evidence_only") is not True:
        raise ValidationError("budget_policy.evidence_only must be true")

    for key in REQUIRED_BUDGET_FALSE_FLAGS:
        if policy.get(key) is not False:
            raise ValidationError(f"budget_policy.{key} must be false")

    max_files = policy.get("max_files_per_ai_context")
    max_lines = policy.get("max_lines_per_file_excerpt")
    if not isinstance(max_files, int) or max_files > 5:
        raise ValidationError("budget_policy.max_files_per_ai_context must be int <= 5")
    if not isinstance(max_lines, int) or max_lines > 120:
        raise ValidationError("budget_policy.max_lines_per_file_excerpt must be int <= 120")

    if policy.get("max_git_diff_lines_for_ai") != 0:
        raise ValidationError("budget_policy.max_git_diff_lines_for_ai must be 0")

    if policy.get("safety_rule_pack_id") != "SAFETY_RULE_PACK_AB_V1":
        raise ValidationError("budget_policy.safety_rule_pack_id must be SAFETY_RULE_PACK_AB_V1")

    return {
        "phase": policy["phase"],
        "name": policy["name"],
        "status": "PASS",
    }


def validate_snapshot_digest_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    _require_keys(snapshot, REQUIRED_SNAPSHOT_TOP_KEYS, "snapshot_digest")

    if snapshot.get("phase") != "AB-T1":
        raise ValidationError("snapshot_digest.phase must be AB-T1")
    if snapshot.get("status") != "DESIGN_ONLY":
        raise ValidationError("snapshot_digest.status must be DESIGN_ONLY")

    current_state = snapshot.get("current_state")
    if not isinstance(current_state, dict):
        raise ValidationError("snapshot_digest.current_state must be object")
    _require_keys(current_state, REQUIRED_CURRENT_STATE_KEYS, "snapshot_digest.current_state")

    if current_state.get("phase_1m_fix") != "PASS":
        raise ValidationError("snapshot_digest.current_state.phase_1m_fix must be PASS")
    if current_state.get("phase_1n") != "PASS":
        raise ValidationError("snapshot_digest.current_state.phase_1n must be PASS")
    if current_state.get("ab_t0") != "PASS_DESIGN_ONLY_NO_EXECUTION":
        raise ValidationError("snapshot_digest.current_state.ab_t0 mismatch")
    if current_state.get("next_phase") != "Phase 1N-FIX pre-live resnapshot evidence cleanup":
        raise ValidationError("snapshot_digest.current_state.next_phase mismatch")

    safety = snapshot.get("safety")
    if not isinstance(safety, dict):
        raise ValidationError("snapshot_digest.safety must be object")
    _require_keys(safety, REQUIRED_SAFETY_KEYS, "snapshot_digest.safety")

    if safety.get("production_status") != "NO_GO":
        raise ValidationError("snapshot_digest.safety.production_status must be NO_GO")
    if safety.get("execution_status") != "NO_EXECUTION":
        raise ValidationError("snapshot_digest.safety.execution_status must be NO_EXECUTION")

    for key in [
        "live_execution_allowed",
        "production_write_allowed",
        "wordpress_write_allowed",
        "external_api_call_allowed",
        "credential_read_allowed",
        "credential_output_allowed",
    ]:
        if safety.get(key) is not False:
            raise ValidationError(f"snapshot_digest.safety.{key} must be false")

    token_efficiency = snapshot.get("token_efficiency")
    if not isinstance(token_efficiency, dict):
        raise ValidationError("snapshot_digest.token_efficiency must be object")
    _require_keys(token_efficiency, REQUIRED_TOKEN_EFFICIENCY_KEYS, "snapshot_digest.token_efficiency")

    if not isinstance(token_efficiency.get("max_files_per_ai_context"), int) or token_efficiency.get(
        "max_files_per_ai_context"
    ) > 5:
        raise ValidationError("snapshot_digest.token_efficiency.max_files_per_ai_context must be int <= 5")

    if token_efficiency.get("copilot_agent_default_allowed") is not False:
        raise ValidationError("snapshot_digest.token_efficiency.copilot_agent_default_allowed must be false")
    if token_efficiency.get("full_diff_allowed") is not False:
        raise ValidationError("snapshot_digest.token_efficiency.full_diff_allowed must be false")
    if token_efficiency.get("full_log_allowed") is not False:
        raise ValidationError("snapshot_digest.token_efficiency.full_log_allowed must be false")
    if token_efficiency.get("full_evidence_index_allowed") is not False:
        raise ValidationError("snapshot_digest.token_efficiency.full_evidence_index_allowed must be false")

    return {
        "phase": snapshot["phase"],
        "name": snapshot["name"],
        "status": "PASS",
    }


def validate_all(
    budget_policy_path: Path = DEFAULT_BUDGET_POLICY,
    snapshot_digest_path: Path = DEFAULT_SNAPSHOT_DIGEST,
) -> dict[str, Any]:
    budget_path = Path(budget_policy_path)
    snapshot_path = Path(snapshot_digest_path)

    if not budget_path.exists():
        raise ValidationError(f"budget policy file not found: {budget_path}")
    if not snapshot_path.exists():
        raise ValidationError(f"snapshot digest file not found: {snapshot_path}")

    budget_result = validate_token_budget_policy_data(_load_json(budget_path))
    snapshot_result = validate_snapshot_digest_data(_load_json(snapshot_path))

    return {
        "status": "PASS",
        "budget_policy": budget_result,
        "snapshot_digest": snapshot_result,
    }


def main() -> None:
    try:
        result = validate_all()
    except ValidationError as exc:
        raise SystemExit(f"AB-T0.5/AB-T1 validation failed: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

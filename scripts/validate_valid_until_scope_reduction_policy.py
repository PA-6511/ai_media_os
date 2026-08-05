#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POLICY_PATH = Path("config/valid_until_scope_reduction_policy.json")

REQUIRED_INVALIDATED_BY = {
    "input_file_changed",
    "policy_changed",
    "approval_label_changed",
    "credential_state_changed",
    "execution_permission_changed",
    "target_phase_changed",
    "production_boundary_changed",
}

REQUIRED_EXECUTION_APPLIES_TO = {
    "credential_env_creation",
    "external_api_real_call",
    "wordpress_write",
    "wordpress_publish",
    "systemd_timer_start",
    "systemd_timer_enable",
    "rollback_execution",
    "emergency_recovery_or_isolation_release",
}

REQUIRED_PROHIBITED = {
    "no_production_write",
    "no_wordpress_api_call",
    "no_external_api_call",
    "no_credential_read",
    "no_credential_output",
    "no_systemd_operation",
    "no_approval_label_consumption",
    "no_phase_forward_execution",
}


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(policy: dict) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(policy.get("policy_name") == "VALID_UNTIL_SCOPE_REDUCTION_POLICY", "invalid policy_name")
    require(policy.get("status") == "PASS_DESIGN_ONLY_NO_EXECUTION", "status must be PASS_DESIGN_ONLY_NO_EXECUTION")
    require(policy.get("production_status") == "NO_GO", "production_status must be NO_GO")
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "execution_mode must be DRY_RUN_ONLY")
    require(policy.get("valid_until_default_policy") == "DISABLED_FOR_NON_EXECUTION_DECISIONS", "invalid valid_until_default_policy")

    non_execution = policy.get("non_execution_decision_policy", {})
    require(non_execution.get("valid_until_required") is False, "non-execution valid_until_required must be false")
    require(non_execution.get("freshness_policy") == "STATIC_UNTIL_INPUT_CHANGE", "non-execution freshness_policy must be STATIC_UNTIL_INPUT_CHANGE")
    require(non_execution.get("requires_time_based_recheck") is False, "non-execution requires_time_based_recheck must be false")
    require(set(non_execution.get("invalidated_by", [])) >= REQUIRED_INVALIDATED_BY, "non-execution invalidated_by missing required conditions")

    execution_gate = policy.get("execution_gate_policy", {})
    require(execution_gate.get("valid_until_required") is True, "execution gate valid_until_required must be true")
    require(execution_gate.get("freshness_policy") == "SHORT_EXECUTION_WINDOW", "execution gate freshness_policy must be SHORT_EXECUTION_WINDOW")
    require(execution_gate.get("single_use") is True, "execution gate single_use must be true")
    require(execution_gate.get("auto_revoke_after_use") is True, "execution gate auto_revoke_after_use must be true")
    require(set(execution_gate.get("applies_to", [])) >= REQUIRED_EXECUTION_APPLIES_TO, "execution gate applies_to missing required entries")

    prohibited = set(policy.get("prohibited_changes", []))
    require(REQUIRED_PROHIBITED.issubset(prohibited), "prohibited_changes missing required entries")

    return errors


def main() -> int:
    policy = load_policy()
    errors = validate(policy)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: valid_until scope reduction policy is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
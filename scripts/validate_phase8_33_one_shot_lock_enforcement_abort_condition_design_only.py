#!/usr/bin/env python3
import json
from pathlib import Path

from phase8_one_shot_execution_gate_pack_common import (
    GLOBAL_FALSE_FLAGS,
    base_result,
    load_json,
    load_required_evidence,
    resolve_root,
    scan_value_strings,
    validate_previous_evidence,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_33_one_shot_lock_enforcement_abort_condition_design_only_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_33_one_shot_lock_enforcement_abort_condition_design_only_request.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_33_one_shot_lock_enforcement_abort_condition_design_only_result.json"


def validate_phase8_33(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT,
) -> dict:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)

    if not policy_path.exists() or not request_path.exists():
        result = base_result("8-33", "One-shot lock enforcement and abort condition design only")
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["reasons"] = ["missing_policy_or_request"]
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)
    root = resolve_root(policy_path)

    result = base_result("8-33", policy.get("phase_name", "One-shot lock enforcement and abort condition design only"))
    result["target_item_count"] = int(request.get("target_item_count", 1))
    result["lock_exists_simulated"] = bool(request.get("lock_exists_simulated", False))
    result["lock_status"] = "UNSET"

    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    found, payloads, missing = load_required_evidence(root)
    result["previous_evidence_found"] = found
    if not found:
        result["reasons"].append("missing_required_evidence")
        result["reasons"].extend([f"missing:{item}" for item in missing])

    result.update(validate_previous_evidence(payloads, policy_violations))

    if result.get("previous_credentials_not_ready"):
        result["reasons"].append("previous_credentials_not_ready_blocked_reason_recorded")

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    for flag in [
        "execution_allowed",
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "wordpress_draft_creation_allowed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "actual_go_decision_issued",
        "handoff_evidence_generated_for_execution",
    ]:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if policy.get("production_status") != "NO_GO":
        policy_violations.append("policy.production_status must be NO_GO")
    if policy.get("execution") != "DRY_RUN":
        policy_violations.append("policy.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("design_only") is not True:
        policy_violations.append("request.design_only must be true")
    if result["target_item_count"] != 1:
        policy_violations.append("request.target_item_count must be 1")

    markers = list(policy.get("forbidden_value_markers", []))
    scan_value_strings(request, markers, secret_leak_findings)
    scan_value_strings(result, markers, secret_leak_findings)

    result["policy_violations"] = policy_violations
    result["secret_leak_findings"] = secret_leak_findings

    if not found:
        result["final_status"] = "ABORT_MISSING_EVIDENCE"
        result["no_secret_leak_passed"] = False
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["no_secret_leak_passed"] = False
        result["next_step"] = request.get("next_step_if_secret_leak_risk", "abort_without_execution")
    elif result["lock_exists_simulated"]:
        result["final_status"] = "ABORT_ONE_SHOT_LOCK_EXISTS_NO_EXECUTION"
        result["lock_status"] = "LOCK_EXISTS_SIMULATED"
        result["next_step"] = "abort_without_execution"
    else:
        result["final_status"] = "DESIGN_ONLY_ONE_SHOT_LOCK_ABORT_SPEC_READY_NO_EXECUTION"
        result["lock_status"] = "LOCK_CLEAR_SIMULATED"
        result["next_step"] = request.get("next_step_if_design_pass", "phase8_35_final_pre_execution_confirmation_or_dry_run_handoff")

    for key, value in GLOBAL_FALSE_FLAGS.items():
        result[key] = value

    write_json(output_json_path, result)
    return result


def main() -> int:
    result = validate_phase8_33()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "DESIGN_ONLY_ONE_SHOT_LOCK_ABORT_SPEC_READY_NO_EXECUTION",
        "ABORT_ONE_SHOT_LOCK_EXISTS_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())

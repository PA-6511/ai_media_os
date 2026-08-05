#!/usr/bin/env python3
import json
from pathlib import Path

from phase8_pre_execution_approval_pack_common import (
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
DEFAULT_POLICY = ROOT / "config/phase8_31_human_execution_approval_validation_handoff_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_31_human_execution_approval_validation_handoff_request.example.json"
DEFAULT_HUMAN_APPROVAL = ROOT / "exchange/examples/phase8_31_human_execution_approval.example.json"
DEFAULT_PHASE30_RESULT = ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_31_human_execution_approval_validation_handoff_result.json"


def validate_phase8_31(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    human_approval_path: Path = DEFAULT_HUMAN_APPROVAL,
    phase30_result_path: Path = DEFAULT_PHASE30_RESULT,
    output_json_path: Path = DEFAULT_OUTPUT,
) -> dict:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    human_approval_path = Path(human_approval_path)
    phase30_result_path = Path(phase30_result_path)
    output_json_path = Path(output_json_path)

    if not policy_path.exists() or not request_path.exists() or not human_approval_path.exists():
        result = base_result("8-31", "Human execution approval validation / handoff for next phase")
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["reasons"] = ["missing_policy_or_request_or_human_approval"]
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)
    human = load_json(human_approval_path)
    root = resolve_root(policy_path)

    result = base_result("8-31", policy.get("phase_name", "Human execution approval validation / handoff for next phase"))
    result["human_execution_approval_validation_executed"] = True
    result["target_item_count"] = int(request.get("target_item_count", 1))

    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    previous_evidence_found, evidence_payloads, missing = load_required_evidence(root)
    result["previous_evidence_found"] = previous_evidence_found
    if not previous_evidence_found:
        result["reasons"].append("missing_required_evidence")
        result["reasons"].extend([f"missing:{item}" for item in missing])

    s816, s817, s1822, s2325, s2628 = validate_previous_evidence(evidence_payloads, policy_violations)
    result["previous_phase8_16_final_status"] = s816
    result["previous_phase8_17_final_status"] = s817
    result["previous_phase8_18_to_8_22_pack_status"] = s1822
    result["previous_phase8_23_to_8_25_pack_status"] = s2325
    result["previous_phase8_26_to_8_28_pack_status"] = s2628

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
    if result["target_item_count"] != 1:
        policy_violations.append("request.target_item_count must be 1")

    for key in [
        "approved_for_this_phase_execution",
        "approved_for_wordpress_api_call_in_this_phase",
        "approved_for_wordpress_write_in_this_phase",
        "approved_for_draft_creation_in_this_phase",
        "approved_for_publish",
        "approved_for_update",
        "approved_for_delete",
        "approved_for_export",
        "approved_for_unlock",
        "secret_values_included",
    ]:
        if human.get(key) is not False:
            policy_violations.append(f"human.{key} must be false")

    if human.get("target_item_count") != 1:
        policy_violations.append("human.target_item_count must be 1")
    if human.get("human_approval_required") is not True:
        policy_violations.append("human.human_approval_required must be true")

    decision = str(human.get("decision", "")).strip()
    allowed = set(policy.get("allowed_decisions", []))
    result["human_decision"] = decision
    result["human_approval_valid"] = decision in allowed
    if decision not in allowed:
        result["reasons"].append("human decision is outside allowed_decisions")

    if not phase30_result_path.exists():
        result["reasons"].append("missing_phase8_30_result")
        previous_evidence_found = False
        phase30_status = None
    else:
        phase30 = load_json(phase30_result_path)
        phase30_status = phase30.get("final_status")
        result["credentials_ready"] = bool(phase30.get("credentials_ready", False))
        result["credentials_not_ready"] = bool(phase30.get("credentials_not_ready", False))
        result["credential_checks"] = phase30.get("credential_checks", [])
        result["credential_recheck_executed"] = bool(phase30.get("credential_recheck_executed", False))
        result["final_preflight_executed"] = bool(phase30.get("final_preflight_executed", False))
        result["no_secret_leak_passed"] = bool(phase30.get("no_secret_leak_passed", False))

    markers = list(policy.get("forbidden_value_markers", []))
    scan_value_strings(request, markers, secret_leak_findings)
    scan_value_strings(result, markers, secret_leak_findings)

    result["policy_violations"] = policy_violations
    result["secret_leak_findings"] = secret_leak_findings

    if not previous_evidence_found:
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
    elif phase30_status == "FINAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION":
        result["final_status"] = "HUMAN_APPROVAL_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
        result["next_step"] = request.get("next_step_if_blocked", "manual_credential_provisioning_then_recheck")
    elif decision == "APPROVE_SINGLE_DRAFT_CREATE_NEXT_PHASE_ONLY" and phase30_status == "FINAL_PREFLIGHT_READY_BUT_NO_EXECUTION":
        result["final_status"] = "HUMAN_APPROVAL_VALID_FOR_NEXT_PHASE_READY_BUT_NOT_EXECUTED"
        result["next_step"] = request.get("next_step_if_approval_valid", "prepare_next_phase_single_draft_create_gate")
    elif decision == "REQUEST_FIX":
        result["final_status"] = "WARN_REQUEST_FIX_NO_EXECUTION"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif decision == "REJECT":
        result["final_status"] = "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION"
        result["next_step"] = "stop_without_execution"
    elif decision == "ABORT":
        result["final_status"] = "ABORT_BY_HUMAN_NO_EXECUTION"
        result["next_step"] = "stop_without_execution"
    else:
        result["final_status"] = "ABORT_UNKNOWN_DECISION_NO_EXECUTION"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")

    for key, value in GLOBAL_FALSE_FLAGS.items():
        result[key] = value

    write_json(output_json_path, result)
    return result


def main() -> int:
    result = validate_phase8_31()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "HUMAN_APPROVAL_VALID_FOR_NEXT_PHASE_READY_BUT_NOT_EXECUTED",
        "HUMAN_APPROVAL_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION",
        "WARN_REQUEST_FIX_NO_EXECUTION",
        "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION",
        "ABORT_BY_HUMAN_NO_EXECUTION",
        "ABORT_UNKNOWN_DECISION_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())

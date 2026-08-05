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
DEFAULT_POLICY = ROOT / "config/phase8_30_final_preflight_before_single_controlled_draft_creation_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_30_final_preflight_before_single_controlled_draft_creation_request.example.json"
DEFAULT_PHASE29_RESULT = ROOT / "exchange/logs/phase8_29_credential_readiness_recheck_no_secret_leak_gate_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_result.json"


def validate_phase8_30(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    phase29_result_path: Path = DEFAULT_PHASE29_RESULT,
    output_json_path: Path = DEFAULT_OUTPUT,
) -> dict:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    phase29_result_path = Path(phase29_result_path)
    output_json_path = Path(output_json_path)

    if not policy_path.exists() or not request_path.exists():
        result = base_result("8-30", "Final preflight before single controlled draft creation")
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["reasons"] = ["missing_policy_or_request"]
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)
    root = resolve_root(policy_path)

    result = base_result("8-30", policy.get("phase_name", "Final preflight before single controlled draft creation"))
    result["final_preflight_executed"] = True
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

    if not phase29_result_path.exists():
        result["reasons"].append("missing_phase8_29_result")
        previous_evidence_found = False
    else:
        phase29 = load_json(phase29_result_path)
        result["credentials_ready"] = bool(phase29.get("credentials_ready", False))
        result["credentials_not_ready"] = bool(phase29.get("credentials_not_ready", False))
        result["credential_checks"] = phase29.get("credential_checks", [])
        result["credential_recheck_executed"] = bool(phase29.get("credential_recheck_executed", False))
        result["no_secret_leak_passed"] = bool(phase29.get("no_secret_leak_passed", False))
        phase29_status = phase29.get("final_status")

        if phase29_status == "CREDENTIAL_RECHECK_READY_NO_SECRET_LEAK_NO_EXECUTION":
            preflight_ready = True
        elif phase29_status == "CREDENTIAL_RECHECK_NOT_READY_NO_SECRET_OUTPUT_NO_EXECUTION":
            preflight_ready = False
            result["credentials_not_ready"] = True
        else:
            preflight_ready = False
            policy_violations.append("phase8_29 final_status is not accepted")

        result["credentials_ready"] = bool(preflight_ready)

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
    elif result.get("credentials_ready"):
        result["final_status"] = "FINAL_PREFLIGHT_READY_BUT_NO_EXECUTION"
        result["next_step"] = request.get("next_step_if_ready", "phase8_31_human_execution_approval_validation_handoff")
    else:
        result["final_status"] = "FINAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
        result["next_step"] = request.get("next_step_if_not_ready", "manual_credential_provisioning_then_recheck")

    for key, value in GLOBAL_FALSE_FLAGS.items():
        result[key] = value

    write_json(output_json_path, result)
    return result


def main() -> int:
    result = validate_phase8_30()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "FINAL_PREFLIGHT_READY_BUT_NO_EXECUTION",
        "FINAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())

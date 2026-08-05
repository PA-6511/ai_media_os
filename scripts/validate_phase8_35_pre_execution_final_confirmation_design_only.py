#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any

from phase8_one_shot_execution_gate_pack_common import now_iso, scan_value_strings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_35_pre_execution_final_confirmation_design_only_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_35_pre_execution_final_confirmation_design_only_request.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_result.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def base_result() -> dict[str, Any]:
    return {
        "phase": "8-35",
        "phase_name": "Pre-execution final confirmation design only",
        "final_status": "ABORT_POLICY_VIOLATION",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "design_only": True,
        "previous_evidence_found": False,
        "phase8_29_to_8_31_pack_status": None,
        "phase8_32_to_8_34_pack_status": None,
        "credentials_ready": False,
        "credentials_not_ready": False,
        "stop_required": False,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_action_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "executor_action_allowed": False,
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "no_secret_leak_passed": True,
        "reasons": [],
        "policy_violations": [],
        "secret_leak_findings": [],
        "next_step": "abort_without_execution",
        "validated_at": now_iso(),
    }


def validate_phase8_35(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)

    result = base_result()

    if not policy_path.exists() or not request_path.exists():
        result["reasons"].append("missing_policy_or_request")
        result["no_secret_leak_passed"] = False
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)

    result["phase_name"] = str(policy.get("phase_name", result["phase_name"]))
    result["target_item_count"] = int(request.get("target_item_count", 1))

    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    root = resolve_root(policy_path)
    evidence_paths = [root / rel for rel in policy.get("required_evidence", [])]
    if all(path.exists() for path in evidence_paths):
        result["previous_evidence_found"] = True
    else:
        result["reasons"].append("missing_required_evidence")
        for path in evidence_paths:
            if not path.exists():
                result["reasons"].append(f"missing:{path.relative_to(root)}")

    phase2931_payload = {}
    phase3234_payload = {}
    if result["previous_evidence_found"]:
        phase2931_payload = load_json(evidence_paths[0])
        phase3234_payload = load_json(evidence_paths[1])

    result["phase8_29_to_8_31_pack_status"] = phase2931_payload.get("pack_status")
    result["phase8_32_to_8_34_pack_status"] = phase3234_payload.get("pack_status")
    result["credentials_ready"] = bool(phase2931_payload.get("credentials_ready", False))
    result["credentials_not_ready"] = bool(phase2931_payload.get("credentials_not_ready", False))

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

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    for flag in [
        "execution_allowed",
        "wordpress_api_call_allowed",
        "wordpress_api_call_attempted",
        "wordpress_write_allowed",
        "wordpress_write_executed",
        "wordpress_draft_creation_allowed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "actual_go_decision_issued",
        "handoff_evidence_generated_for_execution",
    ]:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if request.get("stop_if_credentials_not_ready") is not True:
        policy_violations.append("request.stop_if_credentials_not_ready must be true")
    if request.get("credentials_ready_does_not_execute") is not True:
        policy_violations.append("request.credentials_ready_does_not_execute must be true")

    accepted_2931 = set(policy.get("accepted_phase8_29_to_8_31_statuses", []))
    expected_3234 = policy.get("accepted_phase8_32_to_8_34_status")

    if result["previous_evidence_found"]:
        if result["phase8_29_to_8_31_pack_status"] not in accepted_2931:
            policy_violations.append("phase8_29_to_8_31 pack status is not accepted")
        if result["phase8_32_to_8_34_pack_status"] != expected_3234:
            policy_violations.append("phase8_32_to_8_34 pack status is not accepted")

    markers = list(policy.get("forbidden_value_markers", []))
    scan_value_strings(request, markers, secret_leak_findings)
    scan_value_strings(result, markers, secret_leak_findings)

    result["policy_violations"] = policy_violations
    result["secret_leak_findings"] = secret_leak_findings

    if not result["previous_evidence_found"]:
        result["final_status"] = "ABORT_MISSING_EVIDENCE"
        result["no_secret_leak_passed"] = False
        result["next_step"] = str(request.get("next_step_if_violation", "abort_without_execution"))
    elif policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["next_step"] = str(request.get("next_step_if_violation", "abort_without_execution"))
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["no_secret_leak_passed"] = False
        result["next_step"] = str(request.get("next_step_if_violation", "abort_without_execution"))
    elif result["credentials_not_ready"]:
        result["final_status"] = "PRE_EXECUTION_FINAL_CONFIRMATION_STOP_CREDENTIALS_NOT_READY_NO_EXECUTION"
        result["stop_required"] = True
        result["next_step"] = str(request.get("next_step_if_credentials_not_ready", "stop_and_wait_for_credentials"))
    elif result["credentials_ready"]:
        result["final_status"] = "PRE_EXECUTION_FINAL_CONFIRMATION_READY_FOR_PHASE8_36_DRY_RUN_HANDOFF_NO_EXECUTION"
        result["stop_required"] = False
        result["next_step"] = str(request.get("next_step_if_credentials_ready", "phase8_36_one_shot_draft_creation_dry_run_handoff"))
    else:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
        result["next_step"] = str(request.get("next_step_if_violation", "abort_without_execution"))

    write_json(output_json_path, result)
    return result


def main() -> int:
    result = validate_phase8_35()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PRE_EXECUTION_FINAL_CONFIRMATION_STOP_CREDENTIALS_NOT_READY_NO_EXECUTION",
        "PRE_EXECUTION_FINAL_CONFIRMATION_READY_FOR_PHASE8_36_DRY_RUN_HANDOFF_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())

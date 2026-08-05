#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_17_single_controlled_draft_creation_human_approval_handoff_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_17_single_controlled_draft_creation_human_approval_handoff_request.example.json"
DEFAULT_HUMAN_APPROVAL = ROOT / "exchange/examples/phase8_17_single_controlled_draft_creation_human_approval.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root_from_policy(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def _contains_sensitive_marker(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _scan_payload_for_markers(value: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _scan_payload_for_markers(item, markers, findings, f"{path}.{key}")
        return

    if isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_payload_for_markers(item, markers, findings, f"{path}[{idx}]")
        return

    if isinstance(value, str) and _contains_sensitive_marker(value, markers):
        findings.append(f"forbidden_output_marker:{path}")


def _decision_map(decision: str) -> tuple[str, str]:
    mapping = {
        "REQUEST_FIX": ("WARN_REQUEST_FIX_NO_EXECUTION", "WARN_REQUEST_FIX"),
        "REJECT": ("FAIL_REJECTED_BY_HUMAN_NO_EXECUTION", "REJECTED_BY_HUMAN"),
        "ABORT": ("ABORT_BY_HUMAN_NO_EXECUTION", "ABORTED_BY_HUMAN"),
    }
    return mapping.get(decision, ("ABORT_UNKNOWN_DECISION_NO_EXECUTION", "ABORTED_UNKNOWN_DECISION"))


def validate_phase8_17_single_controlled_draft_creation_human_approval_handoff(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    human_approval_path: Path = DEFAULT_HUMAN_APPROVAL,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    human_approval_path = Path(human_approval_path)
    output_json_path = Path(output_json_path)

    reasons: list[str] = []
    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    required_files = [
        ("policy", policy_path),
        ("request", request_path),
        ("human_approval", human_approval_path),
    ]
    missing_primitives = [name for name, path in required_files if not path.exists()]

    if missing_primitives:
        result = {
            "phase": "8-17",
            "phase_name": "Single controlled draft creation human approval handoff",
            "final_status": "ABORT_POLICY_VIOLATION",
            "handoff_status": "ABORTED_POLICY_VIOLATION",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "previous_phase": "8-16",
            "previous_final_status": None,
            "previous_evidence_found": False,
            "credentials_ready": False,
            "credentials_not_ready": False,
            "no_secret_leak_passed": False,
            "human_decision": None,
            "human_approval_valid": False,
            "target_item_count": 1,
            "execution_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_api_call_attempted": False,
            "wordpress_write_allowed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "approve_draft_create_only_currently_allowed": False,
            "unlock_in_this_phase": False,
            "secret_values_output": False,
            "secret_values_written": False,
            "secret_values_logged": False,
            "next_step": "abort_without_execution",
            "reasons": [f"missing_file:{name}" for name in missing_primitives],
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    policy = _load_json(policy_path)
    request = _load_json(request_path)
    human = _load_json(human_approval_path)
    base_root = _resolve_root_from_policy(policy_path)

    markers = list(policy.get("no_secret_leak_detection", {}).get("forbidden_markers", []))

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    if policy.get("production_status") != "NO_GO":
        policy_violations.append("policy.production_status must be NO_GO")
    if policy.get("execution") != "DRY_RUN":
        policy_violations.append("policy.execution must be DRY_RUN")
    if policy.get("execution_allowed_in_phase8_17") is not False:
        policy_violations.append("policy.execution_allowed_in_phase8_17 must be false")

    request_false_flags = [
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "wordpress_draft_creation_allowed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "execution_allowed",
    ]
    for flag in request_false_flags:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("handoff_only") is not True:
        policy_violations.append("request.handoff_only must be true")
    if request.get("human_approval_required") is not True:
        policy_violations.append("request.human_approval_required must be true")

    target_item_count = int(request.get("target_item_count", 0))
    if target_item_count != 1:
        policy_violations.append("request.target_item_count must be 1")

    if human.get("target_item_count") != 1:
        policy_violations.append("human.target_item_count must be 1")
    if human.get("human_approval_required") is not True:
        policy_violations.append("human.human_approval_required must be true")

    for approval_flag in [
        "approved_for_wordpress_api_call",
        "approved_for_wordpress_write",
        "approved_for_draft_creation",
        "approved_for_publish",
        "approved_for_update",
        "approved_for_delete",
        "approved_for_export",
        "approved_for_unlock",
    ]:
        if human.get(approval_flag) is not False:
            policy_violations.append(f"human.{approval_flag} must be false")

    if human.get("secret_values_included") is not False:
        policy_violations.append("human.secret_values_included must be false")

    evidence_paths = [base_root / rel for rel in policy.get("required_previous_evidence", [])]
    previous_evidence_found = all(path.exists() for path in evidence_paths)
    previous_result_path = next(
        (path for path in evidence_paths if path.name.endswith("_final_gate_result.json")),
        base_root / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json",
    )

    previous_final_status = None
    credentials_ready = False
    credentials_not_ready = False
    no_secret_leak_passed = False

    if not previous_evidence_found:
        reasons.append("missing_required_phase8_16_evidence")
    else:
        previous_result = _load_json(previous_result_path)
        previous_final_status = previous_result.get("final_status")

        accepted = set(policy.get("accepted_phase8_16_statuses", []))
        accepted_from_request = set(request.get("required_previous_final_status", []))
        if previous_final_status not in accepted:
            policy_violations.append("phase8_16 final_status not accepted by policy")
        if accepted_from_request and previous_final_status not in accepted_from_request:
            policy_violations.append("phase8_16 final_status not accepted by request")

        credentials_ready = previous_final_status == "CREDENTIALS_READY_NO_SECRET_LEAK_PASS"
        credentials_not_ready = previous_final_status == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"

        no_secret_leak_passed = bool(previous_result.get("no_secret_leak_passed", False))
        if previous_result.get("secret_values_output") is not False:
            no_secret_leak_passed = False
        if previous_result.get("secret_values_written") is not False:
            no_secret_leak_passed = False
        if previous_result.get("secret_values_logged") is not False:
            no_secret_leak_passed = False
        if previous_result.get("secret_leak_findings"):
            no_secret_leak_passed = False

        if not no_secret_leak_passed:
            reasons.append("phase8_16 no_secret_leak validation failed")

    human_decision = str(human.get("decision", "")).strip()
    allowed_decisions = set(human.get("allowed_decisions", ["APPROVE_HANDOFF_ONLY", "REQUEST_FIX", "REJECT", "ABORT"]))
    human_approval_valid = human_decision in allowed_decisions
    if not human_approval_valid:
        reasons.append("human decision is outside allowed_decisions")

    result: dict[str, Any] = {
        "phase": "8-17",
        "phase_name": policy.get("phase_name", "Single controlled draft creation human approval handoff"),
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "previous_phase": request.get("previous_phase", "8-16"),
        "previous_final_status": previous_final_status,
        "previous_evidence_found": previous_evidence_found,
        "credentials_ready": credentials_ready,
        "credentials_not_ready": credentials_not_ready,
        "no_secret_leak_passed": no_secret_leak_passed,
        "human_decision": human_decision,
        "human_approval_valid": human_approval_valid,
        "target_item_count": target_item_count,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "reasons": reasons,
        "policy_violations": policy_violations,
        "secret_leak_findings": secret_leak_findings,
        "checked_at": _now_iso(),
    }

    _scan_payload_for_markers(result, markers, secret_leak_findings)

    if not previous_evidence_found:
        result["final_status"] = "ABORT_MISSING_PHASE8_16_EVIDENCE"
        result["handoff_status"] = "ABORTED_MISSING_PHASE8_16_EVIDENCE"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["handoff_status"] = "ABORTED_POLICY_VIOLATION"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif secret_leak_findings or not no_secret_leak_passed:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["handoff_status"] = "ABORTED_SECRET_LEAK_RISK"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif human_decision == "APPROVE_HANDOFF_ONLY":
        result["handoff_status"] = "PASS_HANDOFF_ONLY"
        if credentials_ready:
            result["final_status"] = "PASS_HANDOFF_ONLY_CREDENTIALS_READY"
            result["next_step"] = request.get(
                "next_step_if_credentials_ready_and_human_approved",
                "phase8_18_single_controlled_wordpress_draft_creation_execution",
            )
        elif credentials_not_ready:
            result["final_status"] = "PASS_HANDOFF_ONLY_CREDENTIALS_NOT_READY"
            result["next_step"] = "manual_credential_provisioning_then_repeat_phase8_16_or_phase8_16_equivalent_check"
        else:
            result["final_status"] = "ABORT_POLICY_VIOLATION"
            result["handoff_status"] = "ABORTED_POLICY_VIOLATION"
            result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
    elif human_decision in {"REQUEST_FIX", "REJECT", "ABORT"}:
        final_status, handoff_status = _decision_map(human_decision)
        result["final_status"] = final_status
        result["handoff_status"] = handoff_status
        if human_decision == "REQUEST_FIX":
            result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")
        elif human_decision == "REJECT":
            result["next_step"] = request.get("next_step_if_human_rejected", "stop_without_execution")
        else:
            result["next_step"] = "stop_without_execution"
    else:
        result["final_status"] = "ABORT_UNKNOWN_DECISION_NO_EXECUTION"
        result["handoff_status"] = "ABORTED_UNKNOWN_DECISION"
        result["next_step"] = request.get("next_step_if_policy_violation", "abort_without_execution")

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate_phase8_17_single_controlled_draft_creation_human_approval_handoff()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PASS_HANDOFF_ONLY_CREDENTIALS_READY",
        "PASS_HANDOFF_ONLY_CREDENTIALS_NOT_READY",
        "WARN_REQUEST_FIX_NO_EXECUTION",
        "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION",
        "ABORT_BY_HUMAN_NO_EXECUTION",
        "ABORT_UNKNOWN_DECISION_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())

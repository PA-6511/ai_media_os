#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PHASE816_RESULT = "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"
PHASE816_REPORT = "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json"
PHASE817_RESULT = "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json"
PHASE817_REPORT = "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json"
PACK1822_REPORT = "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json"

GLOBAL_FALSE_FLAGS = {
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
    "secret_values_output": False,
    "secret_values_written": False,
    "secret_values_logged": False,
}


EXPECTED_1822_PACK = "PHASE8_18_TO_8_22_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def _scan_value_strings(payload: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(payload, dict):
        for k, v in payload.items():
            _scan_value_strings(v, markers, findings, f"{path}.{k}")
        return

    if isinstance(payload, list):
        for i, v in enumerate(payload):
            _scan_value_strings(v, markers, findings, f"{path}[{i}]")
        return

    if isinstance(payload, str):
        lowered = payload.lower()
        if any(marker in lowered for marker in markers):
            findings.append(f"forbidden_value:{path}")


def _load_required_evidence(root: Path) -> tuple[bool, dict[str, Any], list[str]]:
    required = [
        PHASE816_RESULT,
        PHASE816_REPORT,
        PHASE817_RESULT,
        PHASE817_REPORT,
        PACK1822_REPORT,
    ]
    missing: list[str] = []
    payloads: dict[str, Any] = {}
    for rel in required:
        p = root / rel
        if not p.exists():
            missing.append(rel)
        else:
            if p.suffix == ".json":
                payloads[rel] = load_json(p)
    return len(missing) == 0, payloads, missing


def validate_post_credentials_ready_design_phase(
    policy_path: Path,
    request_path: Path,
    output_json_path: Path,
    pass_status: str,
    next_step_default: str,
    design_flags: dict[str, bool],
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)

    reasons: list[str] = []
    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    if not policy_path.exists() or not request_path.exists():
        result = {
            "phase": "unknown",
            "phase_name": "unknown",
            "final_status": "ABORT_POLICY_VIOLATION",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "design_only": True,
            "previous_evidence_found": False,
            "previous_phase8_16_final_status": None,
            "previous_phase8_17_final_status": None,
            "previous_phase8_18_to_8_22_pack_status": None,
            "target_item_count": 1,
            "no_secret_leak_passed": False,
            "reasons": ["missing_policy_or_request"],
            "next_step": "abort_without_execution",
            **GLOBAL_FALSE_FLAGS,
            **design_flags,
            "lock_created": False,
            "rollback_executed": False,
            "post_run_verification_executed": False,
        }
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)
    root = resolve_root(policy_path)

    previous_evidence_found, evidence_payloads, missing_evidence = _load_required_evidence(root)
    if not previous_evidence_found:
        reasons.append("missing_required_evidence")

    p816 = evidence_payloads.get(PHASE816_RESULT, {})
    p817 = evidence_payloads.get(PHASE817_RESULT, {})
    p1822 = evidence_payloads.get(PACK1822_REPORT, {})

    previous_phase8_16_final_status = p816.get("final_status")
    previous_phase8_17_final_status = p817.get("final_status")
    previous_pack_status = p1822.get("final_status")

    accepted_816 = set(policy.get("accepted_phase8_16_statuses", [
        "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
        "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    ]))
    if previous_phase8_16_final_status and previous_phase8_16_final_status not in accepted_816:
        policy_violations.append("phase8_16 final status is not accepted")

    accepted_817 = set(policy.get("accepted_phase8_17_statuses", [
        "PASS_HANDOFF_ONLY_CREDENTIALS_READY",
        "PASS_HANDOFF_ONLY_CREDENTIALS_NOT_READY",
    ]))
    if previous_phase8_17_final_status and previous_phase8_17_final_status not in accepted_817:
        policy_violations.append("phase8_17 final status is not accepted")

    expected_pack = policy.get("accepted_phase8_18_to_8_22_pack_status", EXPECTED_1822_PACK)
    if previous_pack_status and previous_pack_status != expected_pack:
        policy_violations.append("phase8_18_to_8_22 pack status is not accepted")

    if p816:
        if p816.get("production_status") != "NO_GO":
            policy_violations.append("phase8_16 production_status must be NO_GO")
        if p816.get("wordpress_api_call_attempted") is not False:
            policy_violations.append("phase8_16 wordpress_api_call_attempted must be false")
        if p816.get("wordpress_write_executed") is not False:
            policy_violations.append("phase8_16 wordpress_write_executed must be false")
        if p816.get("wordpress_draft_created") is not False:
            policy_violations.append("phase8_16 wordpress_draft_created must be false")
        if p816.get("no_secret_leak_passed") is not True:
            policy_violations.append("phase8_16 no_secret_leak_passed must be true")

    if p817:
        if p817.get("production_status") != "NO_GO":
            policy_violations.append("phase8_17 production_status must be NO_GO")
        if p817.get("execution_allowed") is not False:
            policy_violations.append("phase8_17 execution_allowed must be false")
        if p817.get("wordpress_api_call_attempted") is not False:
            policy_violations.append("phase8_17 wordpress_api_call_attempted must be false")
        if p817.get("wordpress_write_executed") is not False:
            policy_violations.append("phase8_17 wordpress_write_executed must be false")
        if p817.get("wordpress_draft_created") is not False:
            policy_violations.append("phase8_17 wordpress_draft_created must be false")

    if p1822:
        if p1822.get("production_status") != "NO_GO":
            policy_violations.append("phase8_18_to_8_22 pack production_status must be NO_GO")
        if p1822.get("execution_allowed") is not False:
            policy_violations.append("phase8_18_to_8_22 pack execution_allowed must be false")

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    if policy.get("production_status") != "NO_GO":
        policy_violations.append("policy.production_status must be NO_GO")
    if policy.get("execution") != "DRY_RUN":
        policy_violations.append("policy.execution must be DRY_RUN")
    if policy.get("design_only") is not True:
        policy_violations.append("policy.design_only must be true")

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

    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("design_only") is not True:
        policy_violations.append("request.design_only must be true")
    if int(request.get("target_item_count", 0)) != 1:
        policy_violations.append("request.target_item_count must be 1")

    markers = list(policy.get("forbidden_value_markers", []))
    _scan_value_strings(request, markers, secret_leak_findings)

    result: dict[str, Any] = {
        "phase": policy.get("phase"),
        "phase_name": policy.get("phase_name"),
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "design_only": True,
        "previous_evidence_found": previous_evidence_found,
        "previous_phase8_16_final_status": previous_phase8_16_final_status,
        "previous_phase8_17_final_status": previous_phase8_17_final_status,
        "previous_phase8_18_to_8_22_pack_status": previous_pack_status,
        "target_item_count": int(request.get("target_item_count", 1)),
        "no_secret_leak_passed": True,
        "reasons": reasons + [f"missing:{item}" for item in missing_evidence],
        "policy_violations": policy_violations,
        "secret_leak_findings": secret_leak_findings,
        "next_step": request.get("next_step_if_design_pass", next_step_default),
        **GLOBAL_FALSE_FLAGS,
        **design_flags,
        "lock_created": False,
        "rollback_executed": False,
        "post_run_verification_executed": False,
    }

    _scan_value_strings(result, markers, secret_leak_findings)

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
    else:
        result["final_status"] = pass_status

    write_json(output_json_path, result)
    return result


def build_phase_report(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": result.get("phase"),
        "phase_name": result.get("phase_name"),
        "final_status": result.get("final_status"),
        "production_status": result.get("production_status"),
        "execution": result.get("execution"),
        "design_only": bool(result.get("design_only", True)),
        "previous_evidence_found": bool(result.get("previous_evidence_found", False)),
        "execution_allowed": False,
        "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
        "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
        "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
        "approve_draft_create_only_currently_allowed": False,
        "no_secret_values_output": result.get("secret_values_output") is False
        and result.get("secret_values_written") is False
        and result.get("secret_values_logged") is False,
        "next_step": result.get("next_step"),
        "generated_at": now_iso(),
    }


def build_phase_report_md(report: dict[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "## Phase summary",
        "- This phase is design-only and performs no WordPress execution.",
        "",
        "## Status",
        f"- final_status: {report.get('final_status')}",
        f"- production_status: {report.get('production_status')}",
        f"- execution: {report.get('execution')}",
        f"- design_only: {report.get('design_only')}",
        f"- previous_evidence_found: {report.get('previous_evidence_found')}",
        "",
        "## Safety",
        f"- execution_allowed=false: {report.get('execution_allowed') is False}",
        f"- WordPress API call not executed: {report.get('wordpress_api_call_not_executed')}",
        f"- WordPress write not executed: {report.get('wordpress_write_not_executed')}",
        f"- draft creation not executed: {report.get('draft_creation_not_executed')}",
        f"- approve_draft_create_only_currently_allowed=false: {report.get('approve_draft_create_only_currently_allowed') is False}",
        f"- production remains NO_GO: {report.get('production_status') == 'NO_GO'}",
        f"- no secret values output: {report.get('no_secret_values_output')}",
        "",
        "## Next step",
        f"- {report.get('next_step')}",
    ]
    return "\n".join(lines) + "\n"

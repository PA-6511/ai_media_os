#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def has_forbidden_marker(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def scan_payload_strings_for_forbidden_values(value: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            scan_payload_strings_for_forbidden_values(item, markers, findings, f"{path}.{key}")
        return

    if isinstance(value, list):
        for idx, item in enumerate(value):
            scan_payload_strings_for_forbidden_values(item, markers, findings, f"{path}[{idx}]")
        return

    if isinstance(value, str) and has_forbidden_marker(value, markers):
        findings.append(f"forbidden_value:{path}")


def validate_design_only_phase(
    policy_path: Path,
    request_path: Path,
    output_json_path: Path,
    fallback_next_step: str,
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
            "phase_status": "DESIGN_ONLY",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "execution_allowed": False,
            "previous_evidence_found": False,
            "no_secret_leak_passed": False,
            "next_step": "abort_without_execution",
            "reasons": ["missing_policy_or_request"],
            "policy_violations": [],
            "secret_leak_findings": [],
            "checked_at": now_iso(),
            **GLOBAL_FALSE_FLAGS,
        }
        write_json(output_json_path, result)
        return result

    policy = load_json(policy_path)
    request = load_json(request_path)
    root = resolve_root(policy_path)

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
    if int(request.get("target_item_count", 0)) != 1:
        policy_violations.append("request.target_item_count must be 1")

    evidence_paths = [root / rel for rel in policy.get("required_previous_evidence", [])]
    previous_evidence_found = all(path.exists() for path in evidence_paths)
    if not previous_evidence_found:
        reasons.append("missing_required_evidence")

    result: dict[str, Any] = {
        "phase": policy.get("phase"),
        "phase_name": policy.get("phase_name"),
        "phase_status": policy.get("phase_status", "DESIGN_ONLY"),
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "previous_evidence_found": previous_evidence_found,
        "no_secret_leak_required": bool(request.get("no_secret_leak_required", True)),
        "no_secret_leak_passed": True,
        "next_step": fallback_next_step,
        "reasons": reasons,
        "policy_violations": policy_violations,
        "secret_leak_findings": secret_leak_findings,
        "checked_at": now_iso(),
        **GLOBAL_FALSE_FLAGS,
    }

    markers = list(policy.get("forbidden_value_markers", []))
    scan_payload_strings_for_forbidden_values(result, markers, secret_leak_findings)

    if not previous_evidence_found:
        result["final_status"] = "ABORT_MISSING_EVIDENCE"
        result["no_secret_leak_passed"] = False
    elif policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["no_secret_leak_passed"] = False
    else:
        result["final_status"] = policy.get("pass_status", "DESIGN_ONLY_PASS_NO_EXECUTION")

    write_json(output_json_path, result)
    return result


def build_design_only_report(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": result.get("phase"),
        "phase_name": result.get("phase_name"),
        "final_status": result.get("final_status"),
        "phase_status": result.get("phase_status"),
        "previous_evidence_found": bool(result.get("previous_evidence_found", False)),
        "no_secret_leak_passed": bool(result.get("no_secret_leak_passed", False)),
        "execution_allowed": False,
        "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
        "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
        "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
        "production_status": result.get("production_status", "NO_GO"),
        "next_step": result.get("next_step"),
        "reasons": result.get("reasons", []),
        "generated_at": now_iso(),
    }


def build_design_only_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Phase {report.get('phase')} Design Only Report",
        "",
        "## Summary",
        "- This phase is design only and does not execute WordPress operations.",
        "",
        "## Final status",
        f"- final_status: {report.get('final_status')}",
        f"- phase_status: {report.get('phase_status')}",
        f"- previous_evidence_found: {report.get('previous_evidence_found')}",
        f"- no_secret_leak_passed: {report.get('no_secret_leak_passed')}",
        "",
        "## Execution safety",
        f"- execution_allowed: {report.get('execution_allowed')}",
        f"- WordPress API call not executed: {report.get('wordpress_api_call_not_executed')}",
        f"- WordPress write not executed: {report.get('wordpress_write_not_executed')}",
        f"- draft creation not executed: {report.get('draft_creation_not_executed')}",
        f"- production remains NO_GO: {report.get('production_status') == 'NO_GO'}",
        "",
        "## Next step",
        f"- {report.get('next_step')}",
    ]
    return "\n".join(lines) + "\n"

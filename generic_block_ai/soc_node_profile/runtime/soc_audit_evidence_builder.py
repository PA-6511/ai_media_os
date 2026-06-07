from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_safeguards() -> dict[str, bool]:
    return {
        "design_only": True,
        "no_execution": True,
        "external_api_call": False,
        "wordpress_write": False,
        "shell_execution": False,
        "credential_operation": False,
        "external_send_executed": False,
        "actual_execution": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
    }


def build_soc_audit_evidence_package(
    *,
    capability_report: dict[str, Any],
    acceptance_result: dict[str, Any],
    runner_result: dict[str, Any],
    core_connection_simulation_result: dict[str, Any],
    human_review_handoff_package: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    request_id = str(
        runner_result.get("request_id")
        or acceptance_result.get("request_id")
        or core_connection_simulation_result.get("request_id")
        or "unknown_request"
    )
    node_id = str(
        runner_result.get("node_id")
        or capability_report.get("node_id")
        or core_connection_simulation_result.get("node_id")
        or "soc_node_001"
    )

    evidence = {
        "soc2_capability_report": str(capability_report.get("schema_version", "unknown")),
        "soc3_acceptance_result": str(acceptance_result.get("schema_version", "unknown")),
        "soc4_runner_result": str(runner_result.get("schema_version", "unknown")),
        "soc5_core_connection_simulation_result": str(core_connection_simulation_result.get("schema_version", "unknown")),
        "soc6_human_review_handoff_package": str(human_review_handoff_package.get("schema_version", "unknown")),
    }

    required = [str(x) for x in policy.get("required_evidence_keys", [])]
    missing = [key for key in required if key not in evidence or evidence[key] == "unknown"]

    return {
        "schema_version": str(policy.get("audit_schema_version", "soc_audit_evidence_package_v1")),
        "phase": "SoC-7",
        "node_id": node_id,
        "request_id": request_id,
        "evidence": evidence,
        "evidence_integrity": {
            "evidence_count": len(evidence),
            "missing_evidence_keys": missing,
            "is_complete": len(missing) == 0,
        },
        "safeguards": _base_safeguards(),
        "timestamp_utc": _now_iso(),
    }


def build_soc_re_evaluation_template(
    *,
    core_connection_simulation_result: dict[str, Any],
    human_review_handoff_package: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_handoff_status = str(human_review_handoff_package.get("handoff_status", "REJECTED_NO_GO_LOCK"))
    source_connection_status = str(core_connection_simulation_result.get("connection_status", "REJECTED"))

    outcome = "CONDITIONAL_GO"
    notes = ["dry-run evidence package is complete", "human review decision is pending"]
    checks = ["confirm evidence continuity", "approve_or_reject next phase"]

    if source_handoff_status == "REJECTED_NO_GO_LOCK" or source_connection_status == "REJECTED":
        outcome = "NO_GO"
        notes = ["connection or handoff is rejected", "NO_GO lock must be preserved"]
        checks = ["confirm rejection evidence", "verify no-go lock continuity"]
    elif source_handoff_status == "BLOCKED_REVIEW_REQUIRED":
        outcome = "CONDITIONAL_GO"
        notes = ["gate blocked path requires manual remediation review"]
        checks = ["investigate blocked reasons", "decide remediation plan"]
    elif source_handoff_status == "QUEUED_FOR_HUMAN_REVIEW":
        outcome = "GO"
        notes = ["ready for human review queue processing", "no execution performed"]
        checks = ["final human signoff", "confirm dry-run only continuity"]

    allowed = {str(x) for x in policy.get("allowed_re_evaluation_outcome", [])}
    if outcome not in allowed:
        outcome = "NO_GO"

    return {
        "schema_version": str(policy.get("reevaluation_schema_version", "soc_re_evaluation_template_v1")),
        "phase": "SoC-7",
        "node_id": str(core_connection_simulation_result.get("node_id", "soc_node_001")),
        "request_id": str(core_connection_simulation_result.get("request_id", "unknown_request")),
        "source_handoff_status": source_handoff_status,
        "source_connection_status": source_connection_status,
        "re_evaluation_outcome": outcome,
        "re_evaluation_notes": notes,
        "required_human_checks": checks,
        "timestamp_utc": _now_iso(),
    }


def validate_soc_audit_evidence_package_contract(package: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("audit_schema_version", "")).strip()
    if expected_schema and str(package.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "evidence",
        "evidence_integrity",
        "safeguards",
        "timestamp_utc",
    ]
    missing_fields = [field for field in required_fields if field not in package]
    if missing_fields:
        failed_checks.append(f"missing_required_fields:{','.join(missing_fields)}")

    evidence = package.get("evidence", {})
    if not isinstance(evidence, dict):
        failed_checks.append("evidence must be an object")
        evidence = {}

    required_evidence_keys = [str(x) for x in policy.get("required_evidence_keys", [])]
    missing_evidence = [key for key in required_evidence_keys if key not in evidence]
    if missing_evidence:
        failed_checks.append(f"missing_required_evidence:{missing_evidence}")

    integrity = package.get("evidence_integrity", {})
    if not isinstance(integrity, dict):
        failed_checks.append("evidence_integrity must be an object")
    else:
        if bool(integrity.get("is_complete", False)) is not True:
            warnings.append("evidence_integrity indicates incomplete package")

    safeguards = package.get("safeguards", {})
    if not isinstance(safeguards, dict):
        failed_checks.append("safeguards must be an object")
        safeguards = {}

    for key in policy.get("must_be_false", []):
        skey = str(key)
        if bool(safeguards.get(skey, True)):
            failed_checks.append(f"safeguards.{skey} must be false")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-7",
        "contract": "audit_evidence_package",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc_re_evaluation_template_contract(template: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("reevaluation_schema_version", "")).strip()
    if expected_schema and str(template.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_handoff_status",
        "source_connection_status",
        "re_evaluation_outcome",
        "re_evaluation_notes",
        "required_human_checks",
        "timestamp_utc",
    ]
    missing_fields = [field for field in required_fields if field not in template]
    if missing_fields:
        failed_checks.append(f"missing_required_fields:{','.join(missing_fields)}")

    allowed_outcomes = {str(x) for x in policy.get("allowed_re_evaluation_outcome", [])}
    if str(template.get("re_evaluation_outcome", "")) not in allowed_outcomes:
        failed_checks.append("re_evaluation_outcome is not allowed")

    if not isinstance(template.get("re_evaluation_notes", []), list) or len(template.get("re_evaluation_notes", [])) == 0:
        failed_checks.append("re_evaluation_notes must be a non-empty array")

    if not isinstance(template.get("required_human_checks", []), list) or len(template.get("required_human_checks", [])) == 0:
        failed_checks.append("required_human_checks must be a non-empty array")

    return {
        "phase": "SoC-7",
        "contract": "re_evaluation_template",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc7_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    violations: list[str] = []

    if str(manifest.get("status", "")).upper() != "DESIGN_ONLY":
        violations.append("manifest.status must remain DESIGN_ONLY")
    if str(manifest.get("production_status", "")).upper() != "NO_GO":
        violations.append("manifest.production_status must remain NO_GO")

    execution_value = str(manifest.get("execution", "")).upper()
    if execution_value not in {"DRY_RUN", "DRY_RUN_ONLY", "NO_EXECUTION"}:
        violations.append("manifest.execution must remain dry-run/no-execution")

    if str(policy.get("status", "")).upper() != "DESIGN_ONLY":
        violations.append("policy.status must remain DESIGN_ONLY")
    if str(policy.get("production_status", "")).upper() != "NO_GO":
        violations.append("policy.production_status must remain NO_GO")
    if str(policy.get("execution_mode", "")).upper() != "NO_EXECUTION":
        violations.append("policy.execution_mode must remain NO_EXECUTION")
    if bool(policy.get("dry_run_only", False)) is not True:
        violations.append("policy.dry_run_only must remain true")

    return violations

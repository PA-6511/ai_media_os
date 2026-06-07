from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_final_closure_audit_declaration(
    governance_loop_continuation: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    summary = governance_loop_continuation.get("continuation_summary", {})
    if not isinstance(summary, dict):
        summary = {}

    return {
        "schema_version": str(policy.get("schema_version", "soc_final_closure_audit_declaration_v1")),
        "phase": "SoC-17",
        "node_id": str(governance_loop_continuation.get("node_id", "soc_node_001")),
        "request_id": str(governance_loop_continuation.get("request_id", "unknown_request")),
        "source_governance_schema": str(governance_loop_continuation.get("schema_version", "")),
        "audit_closure_declared": True,
        "closure_state": str(policy.get("required_closure_state", "AUDIT_CLOSED_NO_GO")),
        "declaration_reason": str(
            policy.get("required_declaration_reason", "FINAL_AUDIT_CLOSURE_REPORTS_RECORD_ONLY")
        ),
        "reports_only": True,
        "record_only": True,
        "no_go_lock_confirmed": True,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "audit_summary": {
            "continuation_ready": bool(governance_loop_continuation.get("continuation_ready", False)),
            "next_cycle_mode": str(governance_loop_continuation.get("next_cycle_mode", "")),
            "sealed_complete": bool(summary.get("sealed_complete", False)),
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_final_closure_audit_declaration_contract(
    declaration: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(declaration.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_governance_schema",
        "audit_closure_declared",
        "closure_state",
        "declaration_reason",
        "reports_only",
        "record_only",
        "no_go_lock_confirmed",
        "execution_allowed",
        "production_status",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "audit_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in declaration]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(declaration.get("source_governance_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_governance_schema is invalid")

    if str(declaration.get("closure_state", "")) != str(policy.get("required_closure_state", "")):
        failed_checks.append("closure_state is invalid")

    if str(declaration.get("declaration_reason", "")) != str(policy.get("required_declaration_reason", "")):
        failed_checks.append("declaration_reason is invalid")

    if str(declaration.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(declaration.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(declaration.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    audit_summary = declaration.get("audit_summary", {})
    if not isinstance(audit_summary, dict):
        failed_checks.append("audit_summary must be an object")

    return {
        "phase": "SoC-17",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc17_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

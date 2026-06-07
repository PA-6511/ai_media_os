from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_terminal_preservation_receipt(
    final_closure_audit_declaration: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    audit_summary = final_closure_audit_declaration.get("audit_summary", {})
    if not isinstance(audit_summary, dict):
        audit_summary = {}

    return {
        "schema_version": str(policy.get("schema_version", "soc_terminal_preservation_receipt_v1")),
        "phase": "SoC-18",
        "node_id": str(final_closure_audit_declaration.get("node_id", "soc_node_001")),
        "request_id": str(final_closure_audit_declaration.get("request_id", "unknown_request")),
        "source_closure_schema": str(final_closure_audit_declaration.get("schema_version", "")),
        "preservation_mode": str(policy.get("required_preservation_mode", "REPORTS_RECORD_PRESERVATION_ONLY")),
        "receipt_status": str(policy.get("required_receipt_status", "PRESERVATION_RECEIVED")),
        "preservation_confirmed": True,
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
        "preservation_summary": {
            "closure_state": str(final_closure_audit_declaration.get("closure_state", "")),
            "sealed_complete": bool(audit_summary.get("sealed_complete", False)),
            "retention_reference": "soc_long_term_audit_retention_package_v1",
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_terminal_preservation_receipt_contract(
    receipt: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(receipt.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_closure_schema",
        "preservation_mode",
        "receipt_status",
        "preservation_confirmed",
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
        "preservation_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in receipt]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(receipt.get("source_closure_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_closure_schema is invalid")

    if str(receipt.get("preservation_mode", "")) != str(policy.get("required_preservation_mode", "")):
        failed_checks.append("preservation_mode is invalid")

    if str(receipt.get("receipt_status", "")) != str(policy.get("required_receipt_status", "")):
        failed_checks.append("receipt_status is invalid")

    if str(receipt.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(receipt.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(receipt.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    summary = receipt.get("preservation_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("preservation_summary must be an object")

    return {
        "phase": "SoC-18",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc18_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

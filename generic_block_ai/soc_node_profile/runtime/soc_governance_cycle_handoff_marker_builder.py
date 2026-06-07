from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_governance_cycle_handoff_marker(
    terminal_preservation_receipt: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": str(policy.get("schema_version", "soc_governance_cycle_handoff_marker_v1")),
        "phase": "SoC-19",
        "node_id": str(terminal_preservation_receipt.get("node_id", "soc_node_001")),
        "request_id": str(terminal_preservation_receipt.get("request_id", "unknown_request")),
        "source_preservation_schema": str(terminal_preservation_receipt.get("schema_version", "")),
        "handoff_state": str(policy.get("required_handoff_state", "NEXT_GOVERNANCE_CYCLE_PENDING")),
        "handoff_mode": str(policy.get("required_handoff_mode", "REPORTS_RECORD_ONLY_HANDOFF")),
        "handoff_marker_issued": True,
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
        "handoff_summary": {
            "receipt_status": str(terminal_preservation_receipt.get("receipt_status", "")),
            "preservation_confirmed": bool(terminal_preservation_receipt.get("preservation_confirmed", False)),
            "next_cycle_trigger": "MANUAL_OR_SCHEDULED_REVIEW_ONLY",
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_governance_cycle_handoff_marker_contract(
    marker: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(marker.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_preservation_schema",
        "handoff_state",
        "handoff_mode",
        "handoff_marker_issued",
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
        "handoff_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in marker]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(marker.get("source_preservation_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_preservation_schema is invalid")

    if str(marker.get("handoff_state", "")) != str(policy.get("required_handoff_state", "")):
        failed_checks.append("handoff_state is invalid")

    if str(marker.get("handoff_mode", "")) != str(policy.get("required_handoff_mode", "")):
        failed_checks.append("handoff_mode is invalid")

    if str(marker.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(marker.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(marker.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    summary = marker.get("handoff_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("handoff_summary must be an object")

    return {
        "phase": "SoC-19",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc19_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

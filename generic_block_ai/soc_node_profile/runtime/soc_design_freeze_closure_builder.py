from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_design_freeze_closure_summary(
    periodic_reverification_checklist: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    checklist_targets = periodic_reverification_checklist.get("checklist_targets", [])
    target_count = len(checklist_targets) if isinstance(checklist_targets, list) else 0
    coverage_complete = bool(periodic_reverification_checklist.get("checklist_summary", {}).get("coverage_complete", False))

    return {
        "schema_version": str(policy.get("schema_version", "soc_design_freeze_closure_summary_v1")),
        "phase": "SoC-14",
        "node_id": str(periodic_reverification_checklist.get("node_id", "soc_node_001")),
        "request_id": str(periodic_reverification_checklist.get("request_id", "unknown_request")),
        "source_checklist_schema": str(periodic_reverification_checklist.get("schema_version", "")),
        "freeze_declared": True,
        "closure_declared": True,
        "closure_status": str(policy.get("required_closure_status", "CLOSED_DESIGN_ONLY")),
        "freeze_reason": str(policy.get("required_freeze_reason", "DESIGN_LINE_CLOSED_REPORTS_ONLY")),
        "reports_only": True,
        "record_only": True,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "closure_summary": {
            "target_count": target_count,
            "coverage_complete": coverage_complete,
            "next_cycle_entry": str(
                periodic_reverification_checklist.get(
                    "next_reverification_trigger",
                    "MANUAL_OR_SCHEDULED_REVIEW_ONLY",
                )
            ),
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_design_freeze_closure_summary_contract(
    summary: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(summary.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_checklist_schema",
        "freeze_declared",
        "closure_declared",
        "closure_status",
        "freeze_reason",
        "reports_only",
        "record_only",
        "execution_allowed",
        "production_status",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "closure_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in summary]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(summary.get("source_checklist_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_checklist_schema is invalid")

    if str(summary.get("closure_status", "")) != str(policy.get("required_closure_status", "")):
        failed_checks.append("closure_status is invalid")

    if str(summary.get("freeze_reason", "")) != str(policy.get("required_freeze_reason", "")):
        failed_checks.append("freeze_reason is invalid")

    if str(summary.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(summary.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(summary.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    closure = summary.get("closure_summary", {})
    if not isinstance(closure, dict):
        failed_checks.append("closure_summary must be an object")

    return {
        "phase": "SoC-14",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc14_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

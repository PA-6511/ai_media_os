from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_periodic_reverification_checklist(
    retention_package: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    required_targets = [str(x) for x in policy.get("required_checklist_targets", [])]
    checklist_targets = list(required_targets)
    missing_targets = [target for target in required_targets if target not in checklist_targets]

    return {
        "schema_version": str(policy.get("schema_version", "soc_periodic_reverification_checklist_v1")),
        "phase": "SoC-13",
        "node_id": str(retention_package.get("node_id", "soc_node_001")),
        "request_id": str(retention_package.get("request_id", "unknown_request")),
        "source_retention_schema": str(retention_package.get("schema_version", "")),
        "schedule_type": str(policy.get("required_schedule_type", "PERIODIC_CHECKLIST_ONLY")),
        "reverify_required": True,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "checklist_targets": checklist_targets,
        "next_reverification_trigger": str(
            policy.get("required_next_reverification_trigger", "MANUAL_OR_SCHEDULED_REVIEW_ONLY")
        ),
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "checklist_summary": {
            "target_count": len(checklist_targets),
            "missing_targets": missing_targets,
            "coverage_complete": len(missing_targets) == 0,
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_periodic_reverification_checklist_contract(
    checklist: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(checklist.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_retention_schema",
        "schedule_type",
        "reverify_required",
        "execution_allowed",
        "production_status",
        "checklist_targets",
        "next_reverification_trigger",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "checklist_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in checklist]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(checklist.get("source_retention_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_retention_schema is invalid")

    if str(checklist.get("schedule_type", "")) != str(policy.get("required_schedule_type", "")):
        failed_checks.append("schedule_type is invalid")

    if str(checklist.get("next_reverification_trigger", "")) != str(
        policy.get("required_next_reverification_trigger", "")
    ):
        failed_checks.append("next_reverification_trigger is invalid")

    if str(checklist.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(checklist.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(checklist.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    targets = checklist.get("checklist_targets", [])
    if not isinstance(targets, list):
        failed_checks.append("checklist_targets must be an array")
        targets = []

    required_targets = [str(x) for x in policy.get("required_checklist_targets", [])]
    missing_targets = [target for target in required_targets if target not in targets]
    if missing_targets:
        failed_checks.append(f"missing_checklist_targets:{missing_targets}")

    summary = checklist.get("checklist_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("checklist_summary must be an object")
    else:
        if bool(summary.get("coverage_complete", False)) is not True:
            warnings.append("periodic checklist coverage is incomplete")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-13",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc13_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

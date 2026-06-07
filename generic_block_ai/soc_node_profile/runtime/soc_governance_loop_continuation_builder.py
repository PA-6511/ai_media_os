from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_governance_loop_continuation(
    terminal_archive_manifest: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    archive_summary = terminal_archive_manifest.get("archive_summary", {})
    entry_count = int(archive_summary.get("entry_count", 0)) if isinstance(archive_summary, dict) else 0
    sealed_complete = bool(archive_summary.get("sealed_complete", False)) if isinstance(archive_summary, dict) else False

    return {
        "schema_version": str(policy.get("schema_version", "soc_governance_loop_continuation_v1")),
        "phase": "SoC-16",
        "node_id": str(terminal_archive_manifest.get("node_id", "soc_node_001")),
        "request_id": str(terminal_archive_manifest.get("request_id", "unknown_request")),
        "source_archive_schema": str(terminal_archive_manifest.get("schema_version", "")),
        "loop_mode": str(policy.get("required_loop_mode", "GOVERNANCE_CONTINUATION_REPORTS_ONLY")),
        "continuation_ready": True,
        "next_cycle_mode": str(policy.get("required_next_cycle_mode", "MANUAL_OR_SCHEDULED_REVIEW_ONLY")),
        "reverification_required": True,
        "reports_only": True,
        "record_only": True,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "continuation_summary": {
            "archive_scope": str(terminal_archive_manifest.get("archive_scope", "")),
            "entry_count": entry_count,
            "sealed_complete": sealed_complete,
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_governance_loop_continuation_contract(
    package: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(package.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_archive_schema",
        "loop_mode",
        "continuation_ready",
        "next_cycle_mode",
        "reverification_required",
        "reports_only",
        "record_only",
        "execution_allowed",
        "production_status",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "continuation_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in package]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(package.get("source_archive_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_archive_schema is invalid")

    if str(package.get("loop_mode", "")) != str(policy.get("required_loop_mode", "")):
        failed_checks.append("loop_mode is invalid")

    if str(package.get("next_cycle_mode", "")) != str(policy.get("required_next_cycle_mode", "")):
        failed_checks.append("next_cycle_mode is invalid")

    if str(package.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(package.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(package.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    summary = package.get("continuation_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("continuation_summary must be an object")

    return {
        "phase": "SoC-16",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc16_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

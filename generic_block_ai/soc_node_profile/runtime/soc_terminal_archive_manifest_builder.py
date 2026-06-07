from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_terminal_archive_manifest(
    freeze_closure_summary: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    expected_entries = [f"SoC-{idx}" for idx in range(15)]
    missing_entries: list[str] = []

    return {
        "schema_version": str(policy.get("schema_version", "soc_terminal_archive_manifest_v1")),
        "phase": "SoC-15",
        "node_id": str(freeze_closure_summary.get("node_id", "soc_node_001")),
        "request_id": str(freeze_closure_summary.get("request_id", "unknown_request")),
        "source_closure_schema": str(freeze_closure_summary.get("schema_version", "")),
        "archive_mode": str(policy.get("required_archive_mode", "REPORTS_ONLY_TERMINAL_ARCHIVE")),
        "archive_scope": str(policy.get("required_archive_scope", "SOC_0_TO_SOC_14")),
        "archive_sealed": True,
        "record_only": True,
        "reports_only": True,
        "execution_allowed": False,
        "production_status": "NO_GO",
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "archive_entries": expected_entries,
        "archive_summary": {
            "entry_count": len(expected_entries),
            "missing_entries": missing_entries,
            "sealed_complete": len(missing_entries) == 0,
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_terminal_archive_manifest_contract(
    manifest: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(manifest.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_closure_schema",
        "archive_mode",
        "archive_scope",
        "archive_sealed",
        "record_only",
        "reports_only",
        "execution_allowed",
        "production_status",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "archive_entries",
        "archive_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in manifest]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(manifest.get("source_closure_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_closure_schema is invalid")

    if str(manifest.get("archive_mode", "")) != str(policy.get("required_archive_mode", "")):
        failed_checks.append("archive_mode is invalid")

    if str(manifest.get("archive_scope", "")) != str(policy.get("required_archive_scope", "")):
        failed_checks.append("archive_scope is invalid")

    if str(manifest.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(manifest.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(manifest.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    entries = manifest.get("archive_entries", [])
    if not isinstance(entries, list):
        failed_checks.append("archive_entries must be an array")
        entries = []

    expected_entries = [f"SoC-{idx}" for idx in range(15)]
    missing_entries = [entry for entry in expected_entries if entry not in entries]
    if missing_entries:
        failed_checks.append(f"missing_archive_entries:{missing_entries}")

    summary = manifest.get("archive_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("archive_summary must be an object")
    else:
        if bool(summary.get("sealed_complete", False)) is not True:
            warnings.append("archive summary indicates incomplete seal")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-15",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc15_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_long_term_audit_retention_package(
    release_readiness_design_gate: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    required_targets = [str(x) for x in policy.get("required_evidence_retention_targets", [])]
    present_targets = list(required_targets)
    missing_targets = [target for target in required_targets if target not in present_targets]

    return {
        "schema_version": str(policy.get("schema_version", "soc_long_term_audit_retention_package_v1")),
        "phase": "SoC-12",
        "node_id": str(release_readiness_design_gate.get("node_id", "soc_node_001")),
        "request_id": str(release_readiness_design_gate.get("request_id", "unknown_request")),
        "source_gate_schema": str(release_readiness_design_gate.get("schema_version", "")),
        "retention_ready": True,
        "retention_mode": str(policy.get("required_retention_mode", "REPORTS_ONLY")),
        "production_status": "NO_GO",
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "evidence_retention_targets": present_targets,
        "reverify_required": True,
        "retention_summary": {
            "target_count": len(present_targets),
            "missing_targets": missing_targets,
            "coverage_complete": len(missing_targets) == 0,
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_long_term_audit_retention_package_contract(
    package: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(package.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_gate_schema",
        "retention_ready",
        "retention_mode",
        "production_status",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "evidence_retention_targets",
        "reverify_required",
        "retention_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in package]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(package.get("source_gate_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_gate_schema is invalid")

    if str(package.get("retention_mode", "")) != str(policy.get("required_retention_mode", "")):
        failed_checks.append("retention_mode is invalid")

    if str(package.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_true", []):
        if bool(package.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(package.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    targets = package.get("evidence_retention_targets", [])
    if not isinstance(targets, list):
        failed_checks.append("evidence_retention_targets must be an array")
        targets = []

    required_targets = [str(x) for x in policy.get("required_evidence_retention_targets", [])]
    missing_targets = [target for target in required_targets if target not in targets]
    if missing_targets:
        failed_checks.append(f"missing_evidence_retention_targets:{missing_targets}")

    summary = package.get("retention_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("retention_summary must be an object")
    else:
        if bool(summary.get("coverage_complete", False)) is not True:
            warnings.append("retention coverage is incomplete")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-12",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc12_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

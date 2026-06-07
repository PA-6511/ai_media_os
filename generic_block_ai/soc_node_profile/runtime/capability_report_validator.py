from __future__ import annotations

from typing import Any


def validate_capability_report_contract(report: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    required_fields = [str(item) for item in policy.get("required_fields", [])]
    missing = [field for field in required_fields if field not in report]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(report.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    allowed_status = {str(item) for item in policy.get("allowed_status", [])}
    if str(report.get("status", "")).strip() not in allowed_status:
        failed_checks.append("status is not allowed")

    allowed_execution_mode = {str(item) for item in policy.get("allowed_execution_mode", [])}
    if str(report.get("execution_mode", "")).strip() not in allowed_execution_mode:
        failed_checks.append("execution_mode is not allowed")

    allowed_task_size = {str(item) for item in policy.get("allowed_task_size", [])}
    if str(report.get("recommended_task_size", "")).strip() not in allowed_task_size:
        failed_checks.append("recommended_task_size is not allowed")

    for key in policy.get("must_be_false", []):
        if bool(report.get(str(key), False)):
            failed_checks.append(f"{key} must be false")

    blocked_caps = set(str(item) for item in report.get("blocked_capabilities", []))
    if not blocked_caps:
        failed_checks.append("blocked_capabilities must be non-empty")

    required_blocked = set(str(item) for item in policy.get("forbidden_blocked_capabilities_missing", []))
    missing_blocked = sorted(item for item in required_blocked if item not in blocked_caps)
    if missing_blocked:
        failed_checks.append(f"blocked_capabilities missing required entries: {missing_blocked}")

    node_id = str(report.get("node_id", "")).strip()
    if not node_id:
        failed_checks.append("node_id is required")

    thermal_status = str(report.get("thermal_status", "")).upper()
    if thermal_status in {"WARM"}:
        warnings.append("thermal_status is WARM")
    if thermal_status in {"HOT", "CRITICAL"}:
        failed_checks.append("thermal_status must not be HOT/CRITICAL in capability report")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-2",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "safeguards": {
            "design_only": True,
            "no_execution": True,
            "external_api_call": False,
            "wordpress_write": False,
            "shell_execution": False,
        },
    }


def validate_soc2_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

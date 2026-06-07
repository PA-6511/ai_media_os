from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_approval_decision(final_recommendation: str) -> str:
    if final_recommendation == "GO":
        return "APPROVE_DESIGN_ONLY"
    if final_recommendation == "CONDITIONAL_GO":
        return "APPROVE_CONDITIONAL_DESIGN_ONLY"
    return "REJECT_KEEP_NO_GO"


def _derive_seal_status(final_recommendation: str) -> str:
    if final_recommendation == "GO":
        return "SEALED_DESIGN_ONLY"
    if final_recommendation == "CONDITIONAL_GO":
        return "SEALED_CONDITIONAL"
    return "SEALED_NO_GO_LOCK"


def build_soc_approval_event_record(
    re_evaluation_report: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    final_recommendation = str(re_evaluation_report.get("final_recommendation", "NO_GO"))
    allowed = {str(x) for x in policy.get("allowed_final_recommendation", [])}
    if final_recommendation not in allowed:
        final_recommendation = "NO_GO"

    return {
        "schema_version": str(policy.get("approval_schema_version", "soc_approval_event_record_v1")),
        "phase": "SoC-9",
        "node_id": str(re_evaluation_report.get("node_id", "soc_node_001")),
        "request_id": str(re_evaluation_report.get("request_id", "unknown_request")),
        "source_report_schema": str(re_evaluation_report.get("schema_version", "")),
        "final_recommendation": final_recommendation,
        "approval_decision": _derive_approval_decision(final_recommendation),
        "approval_event_type": "SOC_DESIGN_REVIEW_APPROVAL_EVENT",
        "record_only": True,
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "production_status": "NO_GO",
        "timestamp_utc": _now_iso(),
    }


def build_soc_final_design_package_seal(
    re_evaluation_report: dict[str, Any],
    approval_event_record: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    final_recommendation = str(re_evaluation_report.get("final_recommendation", "NO_GO"))
    allowed = {str(x) for x in policy.get("allowed_final_recommendation", [])}
    if final_recommendation not in allowed:
        final_recommendation = "NO_GO"

    return {
        "schema_version": str(policy.get("seal_schema_version", "soc_final_design_package_seal_v1")),
        "phase": "SoC-9",
        "node_id": str(re_evaluation_report.get("node_id", "soc_node_001")),
        "request_id": str(re_evaluation_report.get("request_id", "unknown_request")),
        "source_report_schema": str(re_evaluation_report.get("schema_version", "")),
        "source_approval_schema": str(approval_event_record.get("schema_version", "")),
        "seal_status": _derive_seal_status(final_recommendation),
        "seal_type": "SOC_FINAL_DESIGN_PACKAGE_SEAL",
        "record_only": True,
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "production_status": "NO_GO",
        "timestamp_utc": _now_iso(),
    }


def validate_soc_approval_event_record_contract(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("approval_schema_version", "")).strip()
    if expected_schema and str(record.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_report_schema",
        "final_recommendation",
        "approval_decision",
        "approval_event_type",
        "record_only",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "production_status",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in record]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(record.get("source_report_schema", "")) != "soc_re_evaluation_report_v1":
        failed_checks.append("source_report_schema must be soc_re_evaluation_report_v1")

    allowed_final = {str(x) for x in policy.get("allowed_final_recommendation", [])}
    if str(record.get("final_recommendation", "")) not in allowed_final:
        failed_checks.append("final_recommendation is not allowed")

    allowed_decision = {str(x) for x in policy.get("allowed_approval_decision", [])}
    if str(record.get("approval_decision", "")) not in allowed_decision:
        failed_checks.append("approval_decision is not allowed")

    if str(record.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_false", []):
        if bool(record.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    if bool(record.get("record_only", False)) is not True:
        failed_checks.append("record_only must be true")

    return {
        "phase": "SoC-9",
        "contract": "approval_event_record",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc_final_design_package_seal_contract(seal: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("seal_schema_version", "")).strip()
    if expected_schema and str(seal.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_report_schema",
        "source_approval_schema",
        "seal_status",
        "seal_type",
        "record_only",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "production_status",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in seal]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(seal.get("source_report_schema", "")) != "soc_re_evaluation_report_v1":
        failed_checks.append("source_report_schema must be soc_re_evaluation_report_v1")
    if str(seal.get("source_approval_schema", "")) != "soc_approval_event_record_v1":
        failed_checks.append("source_approval_schema must be soc_approval_event_record_v1")

    if str(seal.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_false", []):
        if bool(seal.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    if bool(seal.get("record_only", False)) is not True:
        failed_checks.append("record_only must be true")

    return {
        "phase": "SoC-9",
        "contract": "final_design_package_seal",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc9_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

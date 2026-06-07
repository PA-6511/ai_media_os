from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_release_readiness_design_gate(
    dossier_index: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": str(policy.get("schema_version", "soc_release_readiness_design_gate_v1")),
        "phase": "SoC-11",
        "node_id": str(dossier_index.get("node_id", "soc_node_001")),
        "request_id": str(dossier_index.get("request_id", "unknown_request")),
        "source_dossier_schema": str(dossier_index.get("schema_version", "")),
        "dossier_status": str(dossier_index.get("dossier_status", "INCOMPLETE")),
        "release_ready": False,
        "production_status": "NO_GO",
        "execution_allowed": False,
        "external_dispatch_allowed": False,
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "reason": str(policy.get("required_reason", "DESIGN_GATE_ONLY")),
        "gate_summary": {
            "audit_trace_enabled": bool(dossier_index.get("audit_trace_enabled", False)),
            "reverification_ready": bool(dossier_index.get("reverification_ready", False)),
            "missing_keys": list(dossier_index.get("integrity_summary", {}).get("missing_keys", [])),
        },
        "timestamp_utc": _now_iso(),
    }


def validate_soc_release_readiness_design_gate_contract(
    gate: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    failed_checks: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(gate.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "source_dossier_schema",
        "dossier_status",
        "release_ready",
        "production_status",
        "execution_allowed",
        "external_dispatch_allowed",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "reason",
        "gate_summary",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in gate]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    if str(gate.get("source_dossier_schema", "")) != str(policy.get("required_input_schema", "")):
        failed_checks.append("source_dossier_schema is invalid")

    if str(gate.get("reason", "")) != str(policy.get("required_reason", "")):
        failed_checks.append("reason is invalid")

    if str(gate.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    for key in policy.get("must_be_false", []):
        if bool(gate.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    if str(gate.get("dossier_status", "")) not in {"COMPLETE", "INCOMPLETE"}:
        failed_checks.append("dossier_status must be COMPLETE or INCOMPLETE")

    summary = gate.get("gate_summary", {})
    if not isinstance(summary, dict):
        failed_checks.append("gate_summary must be an object")

    return {
        "phase": "SoC-11",
        "result": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def validate_soc11_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

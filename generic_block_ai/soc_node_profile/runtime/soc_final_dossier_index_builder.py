from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_soc_final_design_dossier_index(
    *,
    node_id: str,
    request_id: str,
    soc9_approval_event_record: dict[str, Any],
    soc9_final_design_package_seal: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    artifact_index = {
        "soc0_node_scaffold": "soc_node_concept.md",
        "soc1_hardware_profile_validation": "soc_hardware_profile_validation_policy.json",
        "soc2_capability_report_contract": "soc_capability_report_v1",
        "soc3_task_acceptance_contract": "soc_task_acceptance_result_v1",
        "soc4_task_runner_contract": "soc_task_runner_result_v1",
        "soc5_core_connection_simulation": "soc_core_connection_simulation_result_v1",
        "soc6_human_review_handoff": "soc_human_review_queue_handoff_package_v1",
        "soc7_audit_evidence_and_reevaluation_template": "soc_audit_evidence_package_v1 + soc_re_evaluation_template_v1",
        "soc8_reports_only_reevaluation_report": "soc_re_evaluation_report_v1",
        "soc9_approval_event_and_final_seal": f"{soc9_approval_event_record.get('schema_version', 'unknown')} + {soc9_final_design_package_seal.get('schema_version', 'unknown')}",
    }

    required = [str(x) for x in policy.get("required_phase_artifacts", [])]
    missing = [key for key in required if key not in artifact_index or "unknown" in str(artifact_index.get(key, ""))]

    status = "COMPLETE" if not missing else "INCOMPLETE"

    return {
        "schema_version": str(policy.get("schema_version", "soc_final_design_dossier_index_v1")),
        "phase": "SoC-10",
        "node_id": node_id,
        "request_id": request_id,
        "dossier_status": status,
        "artifact_index": artifact_index,
        "integrity_summary": {
            "required_count": len(required),
            "present_count": len(required) - len(missing),
            "missing_keys": missing,
        },
        "record_only": True,
        "audit_trace_enabled": True,
        "reverification_ready": True,
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "production_status": "NO_GO",
        "timestamp_utc": _now_iso(),
    }


def validate_soc_final_design_dossier_index_contract(index_doc: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(index_doc.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "dossier_status",
        "artifact_index",
        "integrity_summary",
        "record_only",
        "audit_trace_enabled",
        "reverification_ready",
        "actual_execution",
        "external_send_executed",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "production_status",
        "timestamp_utc",
    ]
    missing_fields = [field for field in required_fields if field not in index_doc]
    if missing_fields:
        failed_checks.append(f"missing_required_fields:{','.join(missing_fields)}")

    artifacts = index_doc.get("artifact_index", {})
    if not isinstance(artifacts, dict):
        failed_checks.append("artifact_index must be an object")
        artifacts = {}

    required_artifacts = [str(x) for x in policy.get("required_phase_artifacts", [])]
    missing_artifacts = [key for key in required_artifacts if key not in artifacts]
    if missing_artifacts:
        failed_checks.append(f"missing_required_phase_artifacts:{missing_artifacts}")

    integrity = index_doc.get("integrity_summary", {})
    if not isinstance(integrity, dict):
        failed_checks.append("integrity_summary must be an object")
    else:
        if int(integrity.get("required_count", -1)) != len(required_artifacts):
            failed_checks.append("integrity_summary.required_count mismatch")
        if bool(integrity.get("missing_keys", [])):
            warnings.append("dossier index has missing artifact keys")

    for key in policy.get("must_be_true", []):
        if bool(index_doc.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(index_doc.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    if str(index_doc.get("production_status", "")) != "NO_GO":
        failed_checks.append("production_status must remain NO_GO")

    if str(index_doc.get("dossier_status", "")) not in {"COMPLETE", "INCOMPLETE"}:
        failed_checks.append("dossier_status must be COMPLETE or INCOMPLETE")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-10",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc10_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_safeguards() -> dict[str, bool]:
    return {
        "design_only": True,
        "no_execution": True,
        "external_api_call": False,
        "wordpress_write": False,
        "shell_execution": False,
        "credential_operation": False,
    }


def build_soc_re_evaluation_report(
    audit_evidence_package: dict[str, Any],
    re_evaluation_template: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    request_id = str(re_evaluation_template.get("request_id") or audit_evidence_package.get("request_id") or "unknown_request")
    node_id = str(re_evaluation_template.get("node_id") or audit_evidence_package.get("node_id") or "soc_node_001")

    source_input = {
        "audit_schema_version": str(audit_evidence_package.get("schema_version", "unknown")),
        "template_schema_version": str(re_evaluation_template.get("schema_version", "unknown")),
        "evidence_complete": bool(audit_evidence_package.get("evidence_integrity", {}).get("is_complete", False)),
        "missing_evidence_keys": list(audit_evidence_package.get("evidence_integrity", {}).get("missing_evidence_keys", [])),
    }

    template_outcome = str(re_evaluation_template.get("re_evaluation_outcome", "NO_GO"))
    final_recommendation = template_outcome

    # Evidence incompleteness must not escalate recommendation above conditional safe path.
    if not source_input["evidence_complete"] and final_recommendation == "GO":
        final_recommendation = "CONDITIONAL_GO"

    allowed = {str(x) for x in policy.get("allowed_final_recommendation", [])}
    if final_recommendation not in allowed:
        final_recommendation = "NO_GO"

    report = {
        "schema_version": str(policy.get("schema_version", "soc_re_evaluation_report_v1")),
        "phase": "SoC-8",
        "node_id": node_id,
        "request_id": request_id,
        "reports_only": True,
        "no_external_dispatch": True,
        "actual_execution": False,
        "external_send_executed": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "final_recommendation": final_recommendation,
        "source_input": source_input,
        "evaluation_summary": {
            "template_outcome": template_outcome,
            "template_notes": list(re_evaluation_template.get("re_evaluation_notes", [])) or ["no notes"],
            "required_human_checks": list(re_evaluation_template.get("required_human_checks", [])) or ["manual review required"],
        },
        "safeguards": _base_safeguards(),
        "timestamp_utc": _now_iso(),
    }
    return report


def validate_soc_re_evaluation_report_contract(report: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(report.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "phase",
        "node_id",
        "request_id",
        "reports_only",
        "no_external_dispatch",
        "actual_execution",
        "final_recommendation",
        "source_input",
        "evaluation_summary",
        "safeguards",
        "timestamp_utc",
    ]
    missing_fields = [field for field in required_fields if field not in report]
    if missing_fields:
        failed_checks.append(f"missing_required_fields:{','.join(missing_fields)}")

    for key in policy.get("must_be_true", []):
        if bool(report.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(report.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    final_rec = str(report.get("final_recommendation", ""))
    allowed_final = {str(x) for x in policy.get("allowed_final_recommendation", [])}
    if final_rec not in allowed_final:
        failed_checks.append("final_recommendation is not allowed")

    source_input = report.get("source_input", {})
    if not isinstance(source_input, dict):
        failed_checks.append("source_input must be an object")
    else:
        req_input_versions = policy.get("required_input_schema_versions", {})
        if str(source_input.get("audit_schema_version", "")) != str(req_input_versions.get("audit_evidence", "")):
            failed_checks.append("source_input.audit_schema_version is invalid")
        if str(source_input.get("template_schema_version", "")) != str(req_input_versions.get("re_evaluation_template", "")):
            failed_checks.append("source_input.template_schema_version is invalid")

        if bool(source_input.get("evidence_complete", True)) is not True:
            warnings.append("report generated from incomplete evidence package")

    safeguards = report.get("safeguards", {})
    if not isinstance(safeguards, dict):
        failed_checks.append("safeguards must be an object")
    else:
        for key in ["external_api_call", "wordpress_write", "shell_execution", "credential_operation"]:
            if bool(safeguards.get(key, True)):
                failed_checks.append(f"safeguards.{key} must be false")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-8",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc8_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

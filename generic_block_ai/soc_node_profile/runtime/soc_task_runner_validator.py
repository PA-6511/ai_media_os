from __future__ import annotations

from typing import Any


def validate_soc_task_runner_result_contract(result: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    expected_schema = str(policy.get("schema_version", "")).strip()
    if expected_schema and str(result.get("schema_version", "")).strip() != expected_schema:
        failed_checks.append(f"schema_version must be {expected_schema}")

    required_fields = [
        "request_id",
        "node_id",
        "task_type",
        "execution_mode",
        "status",
        "decision_reason",
        "acceptance_decision",
        "acceptance_reason",
        "input_metrics",
        "safeguards",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in result]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    allowed_status = {str(item) for item in policy.get("allowed_status", [])}
    if str(result.get("status", "")).strip() not in allowed_status:
        failed_checks.append("status is not allowed")

    allowed_execution_mode = {str(item) for item in policy.get("allowed_execution_mode", [])}
    if str(result.get("execution_mode", "")).strip() not in allowed_execution_mode:
        failed_checks.append("execution_mode is not allowed")

    required_acceptance_decision = str(policy.get("required_acceptance_decision", "PASS")).strip()
    if str(result.get("status", "")) == "PASS":
        if str(result.get("acceptance_decision", "")).strip() != required_acceptance_decision:
            failed_checks.append("acceptance_decision must be PASS when runner status is PASS")

    allowed_candidates = {str(item) for item in policy.get("allowed_classification_candidates", [])}
    candidate = str(result.get("classification_candidate", "")).strip()
    if candidate and candidate not in allowed_candidates:
        failed_checks.append("classification_candidate is not allowed")

    safeguards = result.get("safeguards", {})
    if not isinstance(safeguards, dict):
        failed_checks.append("safeguards must be an object")
        safeguards = {}

    must_be_false = {str(item) for item in policy.get("must_be_false", [])}
    for key in sorted(must_be_false):
        if key in {"external_api_call", "wordpress_write", "shell_execution", "credential_operation"}:
            if bool(safeguards.get(key, True)):
                failed_checks.append(f"safeguards.{key} must be false")
            continue

        if bool(result.get(key, True)):
            failed_checks.append(f"{key} must be false")

    input_metrics = result.get("input_metrics", {})
    if not isinstance(input_metrics, dict):
        failed_checks.append("input_metrics must be an object")
    else:
        if int(input_metrics.get("input_lines", -1)) < 0:
            failed_checks.append("input_metrics.input_lines must be >= 0")
        if int(input_metrics.get("input_chars", -1)) < 0:
            failed_checks.append("input_metrics.input_chars must be >= 0")

    if str(result.get("status", "")) == "ABORT" and result.get("classification_candidate") != "ABORT":
        warnings.append("ABORT status usually uses classification_candidate=ABORT")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-4",
        "result": validation_result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }

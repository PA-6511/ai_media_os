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


def _derive_handoff(connection_status: str, integration_result: str) -> tuple[str, str, list[str]]:
    if connection_status == "REJECTED" or integration_result == "FAIL":
        return (
            "REJECTED_NO_GO_LOCK",
            "CRITICAL",
            ["confirm_rejection_evidence", "keep_no_go_lock", "record_rejection_signoff"],
        )
    if connection_status == "BLOCKED_BY_GATE":
        return (
            "BLOCKED_REVIEW_REQUIRED",
            "HIGH",
            ["investigate_gate_block_reason", "confirm_no_go_lock", "decide_manual_override_or_abort"],
        )
    if connection_status == "REVIEW_REQUIRED":
        return (
            "MANUAL_REVIEW_REQUIRED",
            "HIGH",
            ["manual_risk_review", "decide_queue_or_reject"],
        )
    return (
        "QUEUED_FOR_HUMAN_REVIEW",
        "NORMAL",
        ["review_soc_dry_run_summary", "approve_or_reject_followup"],
    )


def build_soc_human_review_handoff_package(
    simulation_result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    node_id = str(simulation_result.get("node_id", "soc_node_001"))
    request_id = str(simulation_result.get("request_id", "unknown_request"))
    connection_status = str(simulation_result.get("connection_status", "REJECTED"))
    core_receive_rule = str(simulation_result.get("core_receive_rule", "REJECT_AND_KEEP_NO_GO"))
    integration_result = str(simulation_result.get("integration_result", "FAIL"))

    handoff_status, review_priority, required_actions = _derive_handoff(connection_status, integration_result)

    package = {
        "schema_version": "soc_human_review_queue_handoff_package_v1",
        "phase": "SoC-6",
        "node_id": node_id,
        "request_id": request_id,
        "source_connection_status": connection_status,
        "source_core_receive_rule": core_receive_rule,
        "source_integration_result": integration_result,
        "handoff_status": handoff_status,
        "review_queue_target": str(policy.get("required_review_queue_target", "SOC_DRY_RUN_REVIEW_QUEUE")),
        "review_priority": review_priority,
        "required_human_actions": required_actions,
        "human_review_required": True,
        "no_external_dispatch": True,
        "external_send_executed": False,
        "actual_execution": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "evidence_refs": [
            "soc_capability_report_v1",
            "soc_task_runner_result_v1",
            "soc_core_connection_simulation_result_v1",
        ],
        "safeguards": _base_safeguards(),
        "timestamp_utc": _now_iso(),
    }

    return package


def validate_soc_human_review_handoff_package_contract(
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
        "source_connection_status",
        "source_core_receive_rule",
        "source_integration_result",
        "handoff_status",
        "review_queue_target",
        "review_priority",
        "required_human_actions",
        "human_review_required",
        "no_external_dispatch",
        "external_send_executed",
        "actual_execution",
        "freeze_executed",
        "isolation_executed",
        "state_change_executed",
        "safeguards",
        "timestamp_utc",
    ]
    missing = [field for field in required_fields if field not in package]
    if missing:
        failed_checks.append(f"missing_required_fields:{','.join(missing)}")

    allowed_source = {str(item) for item in policy.get("allowed_source_connection_status", [])}
    if str(package.get("source_connection_status", "")) not in allowed_source:
        failed_checks.append("source_connection_status is not allowed")

    allowed_handoff = {str(item) for item in policy.get("allowed_handoff_status", [])}
    if str(package.get("handoff_status", "")) not in allowed_handoff:
        failed_checks.append("handoff_status is not allowed")

    required_target = str(policy.get("required_review_queue_target", "SOC_DRY_RUN_REVIEW_QUEUE"))
    if str(package.get("review_queue_target", "")) != required_target:
        failed_checks.append("review_queue_target is invalid")

    actions = package.get("required_human_actions", [])
    if not isinstance(actions, list) or len(actions) == 0:
        failed_checks.append("required_human_actions must be a non-empty array")

    for key in policy.get("must_be_true", []):
        if bool(package.get(str(key), False)) is not True:
            failed_checks.append(f"{key} must be true")

    for key in policy.get("must_be_false", []):
        if bool(package.get(str(key), True)):
            failed_checks.append(f"{key} must be false")

    safeguards = package.get("safeguards", {})
    if not isinstance(safeguards, dict):
        failed_checks.append("safeguards must be an object")
    else:
        for key in ["external_api_call", "wordpress_write", "shell_execution", "credential_operation"]:
            if bool(safeguards.get(key, True)):
                failed_checks.append(f"safeguards.{key} must be false")

    if str(package.get("source_integration_result", "")) == "WARN":
        warnings.append("handoff created from WARN simulation result")

    result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")
    return {
        "phase": "SoC-6",
        "result": result,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def validate_soc6_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

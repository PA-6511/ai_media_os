from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .capability_report_validator import validate_capability_report_contract
from .soc_task_runner_validator import validate_soc_task_runner_result_contract


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
        "actual_execution": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
    }


def _derive_connection_status(capability_result: str, runner_result: str, runner_status: str) -> tuple[str, str]:
    if capability_result == "FAIL" or runner_result == "FAIL":
        return "REJECTED", "REJECT_AND_KEEP_NO_GO"
    if runner_status == "ABORT":
        return "BLOCKED_BY_GATE", "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE"
    if capability_result == "WARN" or runner_result == "WARN":
        return "REVIEW_REQUIRED", "REQUIRE_HUMAN_REVIEW"
    return "ACCEPT_DRY_RUN_REVIEW_QUEUE", "ACCEPT_DRY_RUN_REVIEW_QUEUE"


def run_soc_core_connection_simulation(
    capability_report: dict[str, Any],
    task_runner_result: dict[str, Any],
    capability_policy: dict[str, Any],
    runner_policy: dict[str, Any],
    simulation_policy: dict[str, Any],
) -> dict[str, Any]:
    capability_validation = validate_capability_report_contract(capability_report, capability_policy)
    runner_validation = validate_soc_task_runner_result_contract(task_runner_result, runner_policy)

    cap_result = str(capability_validation.get("result", "FAIL"))
    run_result = str(runner_validation.get("result", "FAIL"))
    runner_status = str(task_runner_result.get("status", "ABORT"))

    connection_status, core_receive_rule = _derive_connection_status(cap_result, run_result, runner_status)

    integration_result = "PASS"
    if cap_result == "FAIL" or run_result == "FAIL":
        integration_result = "FAIL"
    elif cap_result == "WARN" or run_result == "WARN" or runner_status == "ABORT":
        integration_result = "WARN"

    node_id = str(task_runner_result.get("node_id") or capability_report.get("node_id") or "soc_node_001")
    request_id = str(task_runner_result.get("request_id", "unknown_request"))

    warnings: list[str] = []
    if capability_report.get("node_id") and task_runner_result.get("node_id"):
        if str(capability_report.get("node_id")) != str(task_runner_result.get("node_id")):
            warnings.append("node_id mismatch between capability_report and task_runner_result")

    allowed_connection_status = set(str(item) for item in simulation_policy.get("allowed_connection_status", []))
    failed_checks: list[str] = []
    if connection_status not in allowed_connection_status:
        failed_checks.append("derived connection_status is not allowed by simulation policy")

    safeguards = _base_safeguards()

    return {
        "schema_version": "soc_core_connection_simulation_result_v1",
        "phase": "SoC-5",
        "node_id": node_id,
        "request_id": request_id,
        "integration_result": "FAIL" if failed_checks else integration_result,
        "connection_status": connection_status,
        "core_receive_rule": core_receive_rule,
        "capability_validation": {
            "result": cap_result,
            "failed_checks": list(capability_validation.get("failed_checks", [])),
            "warnings": list(capability_validation.get("warnings", [])),
        },
        "runner_validation": {
            "result": run_result,
            "failed_checks": list(runner_validation.get("failed_checks", [])),
            "warnings": list(runner_validation.get("warnings", [])),
        },
        "failed_checks": failed_checks,
        "warnings": warnings,
        "safeguards": safeguards,
        "timestamp_utc": _now_iso(),
    }


def validate_soc5_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

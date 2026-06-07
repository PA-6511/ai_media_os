from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .task_acceptance_gate import evaluate_task_acceptance_contract


def _classify_lightweight(input_lines: list[str]) -> str:
    normalized = "\n".join(input_lines).lower()
    if any(token in normalized for token in ["abort", "critical", "panic"]):
        return "ABORT"
    if any(token in normalized for token in ["fail", "error"]):
        return "FAIL"
    if "warn" in normalized:
        return "WARN"
    return "INFO"


def _base_safeguards() -> dict[str, bool]:
    return {
        "design_only": True,
        "no_execution": True,
        "external_api_call": False,
        "wordpress_write": False,
        "shell_execution": False,
        "credential_operation": False,
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
    }


def run_soc_dry_run_task(task_request: dict[str, Any]) -> dict[str, Any]:
    gate = evaluate_task_acceptance_contract(task_request)
    now = datetime.now(timezone.utc).isoformat()

    request_id = str(gate.get("request_id", "unknown_request"))
    node_id = str(gate.get("node_id", "soc_node_001"))
    task_type = str(gate.get("task_type", ""))
    requested_execution_mode = str(gate.get("execution_mode", ""))
    input_metrics = gate.get("input_metrics", {"input_lines": 0, "input_chars": 0})

    if gate["decision"] != "PASS":
        return {
            "schema_version": "soc_task_runner_result_v1",
            "request_id": request_id,
            "node_id": node_id,
            "task_type": task_type,
            "execution_mode": "DRY_RUN_ONLY",
            "requested_execution_mode": requested_execution_mode,
            "status": "ABORT",
            "decision_reason": gate["reason"],
            "acceptance_decision": gate["decision"],
            "acceptance_reason": gate["reason"],
            "summary": "Task rejected by SoC-3 acceptance gate.",
            "classification_candidate": "ABORT",
            "input_metrics": input_metrics,
            "safeguards": _base_safeguards(),
            "freeze_recommendation": "review_required",
            "freeze_executed": False,
            "isolation_executed": False,
            "state_change_executed": False,
            "wordpress_write_executed": False,
            "publish_allowed": False,
            "timestamp_utc": now,
        }

    raw_lines = task_request.get("input_lines", [])
    input_lines = [str(item) for item in raw_lines] if isinstance(raw_lines, list) else []
    summary = f"Received {len(input_lines)} lines. DRY_RUN lightweight analysis only."
    classification_candidate = _classify_lightweight(input_lines)

    return {
        "schema_version": "soc_task_runner_result_v1",
        "request_id": request_id,
        "node_id": node_id,
        "task_type": task_type,
        "execution_mode": "DRY_RUN_ONLY",
        "requested_execution_mode": requested_execution_mode,
        "status": "PASS",
        "decision_reason": gate["reason"],
        "acceptance_decision": gate["decision"],
        "acceptance_reason": gate["reason"],
        "summary": summary,
        "classification_candidate": classification_candidate,
        "input_metrics": input_metrics,
        "safeguards": _base_safeguards(),
        "freeze_recommendation": "manual_review",
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "timestamp_utc": now,
    }


def validate_soc4_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

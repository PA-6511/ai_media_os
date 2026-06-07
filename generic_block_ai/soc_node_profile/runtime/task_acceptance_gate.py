from __future__ import annotations

from typing import Any


ALLOWED_TASK_TYPES = {
    "log_summary",
    "lightweight_monitor",
    "anomaly_hint",
    "policy_precheck",
    "short_text_generation",
    "classification",
}

BLOCKED_TASK_TYPES = {
    "wordpress_publish",
    "production_write",
    "credential_operation",
    "external_send",
    "shell_execution",
    "delete_operation",
    "bulk_generation",
}


def evaluate_task_acceptance(task_request: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_task_acceptance_contract(task_request)
    return {"decision": result["decision"], "reason": result["reason"]}


def _compute_input_metrics(task_request: dict[str, Any]) -> tuple[int, int]:
    input_lines_raw = task_request.get("input_lines", [])
    if isinstance(input_lines_raw, list):
        lines = [str(item) for item in input_lines_raw]
    else:
        lines = []

    if lines:
        input_lines = len(lines)
        input_chars = sum(len(line) for line in lines)
        return input_lines, input_chars

    input_text = str(task_request.get("input_text", ""))
    if input_text:
        return len(input_text.splitlines()) or 1, len(input_text)

    return 0, 0


def evaluate_task_acceptance_contract(
    task_request: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    applied_policy = dict(policy or {})

    required_execution_mode = str(applied_policy.get("required_execution_mode", "DRY_RUN_ONLY"))
    max_input_lines = int(applied_policy.get("max_input_lines", 200))
    max_input_chars = int(applied_policy.get("max_input_chars", 20000))
    allowed_task_types = set(applied_policy.get("allowed_task_types", sorted(ALLOWED_TASK_TYPES)))
    blocked_task_types = set(applied_policy.get("blocked_task_types", sorted(BLOCKED_TASK_TYPES)))

    request_id = str(task_request.get("request_id", "unknown_request")).strip() or "unknown_request"
    node_id = str(task_request.get("node_id", "soc_node_001")).strip() or "soc_node_001"
    task_type = str(task_request.get("task_type", "")).strip()
    constraints = task_request.get("constraints", {})
    execution_mode = str((constraints or {}).get("execution_mode", task_request.get("execution_mode", ""))).strip()
    input_lines, input_chars = _compute_input_metrics(task_request)

    decision = "ABORT"
    reason = "unsupported_task_type"
    reason_codes = ["unsupported_task_type"]

    if not task_type:
        reason = "missing_task_type"
        reason_codes = ["missing_task_type"]
    elif execution_mode != required_execution_mode:
        reason = f"invalid_execution_mode:{execution_mode or 'EMPTY'}"
        reason_codes = ["invalid_execution_mode"]
    elif input_lines > max_input_lines:
        reason = f"input_lines_exceeded:{input_lines}>{max_input_lines}"
        reason_codes = ["input_lines_exceeded"]
    elif input_chars > max_input_chars:
        reason = f"input_chars_exceeded:{input_chars}>{max_input_chars}"
        reason_codes = ["input_chars_exceeded"]
    elif task_type in blocked_task_types:
        reason = f"blocked_task_type:{task_type}"
        reason_codes = ["blocked_task_type"]
    elif task_type in allowed_task_types:
        decision = "PASS"
        reason = f"allowed_task_type:{task_type}"
        reason_codes = ["allowed_task_type"]
    else:
        reason = f"unsupported_task_type:{task_type}"
        reason_codes = ["unsupported_task_type"]

    return {
        "schema_version": "soc_task_acceptance_result_v1",
        "request_id": request_id,
        "node_id": node_id,
        "task_type": task_type,
        "execution_mode": execution_mode,
        "decision": decision,
        "reason": reason,
        "reason_codes": reason_codes,
        "input_metrics": {
            "input_lines": input_lines,
            "input_chars": input_chars,
        },
        "enforced_limits": {
            "max_input_lines": max_input_lines,
            "max_input_chars": max_input_chars,
        },
        "safeguards": {
            "design_only": True,
            "no_execution": True,
            "external_api_call": False,
            "wordpress_write": False,
            "shell_execution": False,
            "credential_operation": False,
        },
    }


def validate_soc3_phase_constraints(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
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

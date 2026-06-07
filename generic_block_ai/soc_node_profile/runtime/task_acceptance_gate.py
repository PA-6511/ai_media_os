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
    task_type = str(task_request.get("task_type", "")).strip()

    if not task_type:
        return {"decision": "ABORT", "reason": "missing_task_type"}

    if task_type in BLOCKED_TASK_TYPES:
        return {"decision": "ABORT", "reason": f"blocked_task_type:{task_type}"}

    if task_type in ALLOWED_TASK_TYPES:
        return {"decision": "PASS", "reason": f"allowed_task_type:{task_type}"}

    return {"decision": "ABORT", "reason": f"unsupported_task_type:{task_type}"}

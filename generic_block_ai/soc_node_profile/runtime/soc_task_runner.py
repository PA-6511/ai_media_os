from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .task_acceptance_gate import evaluate_task_acceptance


def run_soc_dry_run_task(task_request: dict[str, Any]) -> dict[str, Any]:
    gate = evaluate_task_acceptance(task_request)
    now = datetime.now(timezone.utc).isoformat()

    if gate["decision"] != "PASS":
        return {
            "status": "ABORT",
            "decision_reason": gate["reason"],
            "freeze_recommendation": "review_required",
            "freeze_executed": False,
            "isolation_executed": False,
            "state_change_executed": False,
            "wordpress_write_executed": False,
            "publish_allowed": False,
            "timestamp_utc": now,
        }

    input_lines = task_request.get("input_lines", [])
    summary = f"Received {len(input_lines)} lines. DRY_RUN analysis only."
    warn_candidate = "WARN" if len(input_lines) >= 1 else "INFO"

    return {
        "status": "PASS",
        "decision_reason": gate["reason"],
        "summary": summary,
        "classification_candidate": warn_candidate,
        "freeze_recommendation": "manual_review",
        "freeze_executed": False,
        "isolation_executed": False,
        "state_change_executed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "timestamp_utc": now,
    }

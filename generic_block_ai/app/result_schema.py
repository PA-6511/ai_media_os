from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ALLOWED_STATUS = {"success", "blocked", "error"}
ALLOWED_DECISION = {"decision", "recheck", "human_review"}


def _ensure_list_of_strings(items: list[Any], field_name: str) -> list[str]:
    normalized = [str(item) for item in items]
    if any(not item for item in normalized):
        raise ValueError(f"{field_name} includes an empty value")
    return normalized


def build_block_result(
    *,
    status: str,
    decision: str,
    summary: str,
    risk_level: str,
    needs_approval: bool,
    mode: str,
    actual_execution: bool,
    actions: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    block_id: str,
    version: str,
) -> dict[str, Any]:
    normalized_status = status.strip().lower()
    normalized_decision = decision.strip().lower()
    normalized_mode = mode.strip().lower()

    if normalized_status not in ALLOWED_STATUS:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUS)}")
    if normalized_decision not in ALLOWED_DECISION:
        raise ValueError(f"decision must be one of {sorted(ALLOWED_DECISION)}")
    if normalized_mode != "dry_run":
        raise ValueError("mode must be dry_run for Phase G-1")
    if actual_execution:
        raise ValueError("actual_execution must remain false for Phase G-1")

    if not summary.strip():
        raise ValueError("summary is required")
    if not block_id.strip():
        raise ValueError("block_id is required")
    if not version.strip():
        raise ValueError("version is required")

    result_actions = actions or []
    if any(not isinstance(action, dict) for action in result_actions):
        raise ValueError("actions must be a list of objects")

    result_warnings = _ensure_list_of_strings(warnings or [], "warnings")
    result_errors = _ensure_list_of_strings(errors or [], "errors")

    return {
        "status": normalized_status,
        "decision": normalized_decision,
        "summary": summary,
        "risk_level": risk_level,
        "needs_approval": bool(needs_approval),
        "mode": normalized_mode,
        "actual_execution": False,
        "actions": result_actions,
        "warnings": result_warnings,
        "errors": result_errors,
        "meta": {
            "block_id": block_id,
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

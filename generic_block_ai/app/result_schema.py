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


def _ensure_reason_codes(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("reason_codes must be a list of objects")

        action_type = str(item.get("action_type", "")).strip()
        classification = str(item.get("classification", "")).strip()
        reason = str(item.get("reason", "")).strip()

        if not classification:
            raise ValueError("reason_codes[].classification is required")
        if not reason:
            raise ValueError("reason_codes[].reason is required")

        normalized.append(
            {
                "action_type": action_type,
                "classification": classification,
                "reason": reason,
            }
        )

    return normalized


def _ensure_task_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    required_scores = ("impact_score", "risk_score", "confidence_score", "priority_score")

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("task_candidates must be a list of objects")

        action_type = str(item.get("action_type", "")).strip()
        classification = str(item.get("classification", "")).strip()
        if classification not in {"allow", "block", "needs_review"}:
            raise ValueError("task_candidates[].classification must be allow|block|needs_review")

        for field_name in required_scores:
            value = item.get(field_name)
            if not isinstance(value, int):
                raise ValueError(f"task_candidates[].{field_name} must be int")
            if value < 0 or value > 100:
                raise ValueError(f"task_candidates[].{field_name} must be between 0 and 100")

        normalized.append(
            {
                "candidate_id": str(item.get("candidate_id", "")).strip(),
                "action_type": action_type,
                "classification": classification,
                "impact_score": item["impact_score"],
                "risk_score": item["risk_score"],
                "confidence_score": item["confidence_score"],
                "priority_score": item["priority_score"],
                "action": item.get("action", {}),
            }
        )

    return normalized


def _ensure_rejected_task_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("rejected_task_candidates must be a list of objects")

        reasons = item.get("rejection_reasons", [])
        if not isinstance(reasons, list) or not reasons:
            raise ValueError("rejected_task_candidates[].rejection_reasons must be a non-empty array")

        normalized_reasons: list[dict[str, str]] = []
        for reason in reasons:
            if not isinstance(reason, dict):
                raise ValueError("rejected_task_candidates[].rejection_reasons[] must be objects")
            code = str(reason.get("code", "")).strip()
            message = str(reason.get("message", "")).strip()
            if not code:
                raise ValueError("rejected_task_candidates[].rejection_reasons[].code is required")
            if not message:
                raise ValueError("rejected_task_candidates[].rejection_reasons[].message is required")
            normalized_reasons.append({"code": code, "message": message})

        normalized.append({**item, "rejection_reasons": normalized_reasons})

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
    blocked_actions: list[dict[str, Any]] | None = None,
    needs_review_actions: list[dict[str, Any]] | None = None,
    task_candidates: list[dict[str, Any]] | None = None,
    rejected_task_candidates: list[dict[str, Any]] | None = None,
    reason_codes: list[dict[str, Any]] | None = None,
    review_required_fields: list[str] | None = None,
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

    result_blocked_actions = blocked_actions or []
    if any(not isinstance(action, dict) for action in result_blocked_actions):
        raise ValueError("blocked_actions must be a list of objects")

    result_needs_review_actions = needs_review_actions or []
    if any(not isinstance(action, dict) for action in result_needs_review_actions):
        raise ValueError("needs_review_actions must be a list of objects")

    result_warnings = _ensure_list_of_strings(warnings or [], "warnings")
    result_errors = _ensure_list_of_strings(errors or [], "errors")
    result_review_required_fields = _ensure_list_of_strings(
        review_required_fields or [], "review_required_fields"
    )
    result_task_candidates = _ensure_task_candidates(task_candidates or [])
    result_rejected_task_candidates = _ensure_rejected_task_candidates(rejected_task_candidates or [])
    result_reason_codes = _ensure_reason_codes(reason_codes or [])

    return {
        "status": normalized_status,
        "decision": normalized_decision,
        "summary": summary,
        "risk_level": risk_level,
        "needs_approval": bool(needs_approval),
        "mode": normalized_mode,
        "actual_execution": False,
        "actions": result_actions,
        "blocked_actions": result_blocked_actions,
        "needs_review_actions": result_needs_review_actions,
        "task_candidates": result_task_candidates,
        "rejected_task_candidates": result_rejected_task_candidates,
        "reason_codes": result_reason_codes,
        "review_required_fields": result_review_required_fields,
        "warnings": result_warnings,
        "errors": result_errors,
        "meta": {
            "block_id": block_id,
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

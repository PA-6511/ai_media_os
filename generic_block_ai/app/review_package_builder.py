from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_task_id(source_task_id: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in source_task_id.strip())
    return normalized or "unknown_task"


def _derive_scope(task_candidates: list[dict[str, Any]], rejected_task_candidates: list[dict[str, Any]]) -> str:
    accepted_count = len(task_candidates)
    rejected_count = len(rejected_task_candidates)
    if accepted_count == 0 and rejected_count > 0:
        return "none"
    if accepted_count <= 2:
        return "limited"
    return "moderate"


def _derive_risk_assessment(
    task_candidates: list[dict[str, Any]],
    rejected_task_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    highest_risk = 0
    for item in task_candidates:
        highest_risk = max(highest_risk, int(item.get("risk_score", 0)))
    for item in rejected_task_candidates:
        highest_risk = max(highest_risk, int(item.get("risk_score", 0)))

    risk_level = "low"
    if highest_risk >= 80:
        risk_level = "high"
    elif highest_risk >= 50:
        risk_level = "medium"

    return {
        "level": risk_level,
        "highest_risk_score": highest_risk,
        "blocked_count": len([item for item in rejected_task_candidates if item.get("classification") == "block"]),
        "needs_review_count": len(
            [item for item in task_candidates if item.get("classification") == "needs_review"]
        ),
    }


def build_review_package(
    block_result: dict[str, Any],
    *,
    source_task_id: str,
    approver: str = "human_reviewer",
) -> dict[str, Any]:
    generated_at = _utc_now_iso()
    task_key = _safe_task_id(source_task_id)
    proposal_id = f"review_package_{task_key}"

    block_id = str(block_result.get("meta", {}).get("block_id", "generic_block"))
    task_candidates = list(block_result.get("task_candidates", []))
    rejected_task_candidates = list(block_result.get("rejected_task_candidates", []))

    scope = _derive_scope(task_candidates, rejected_task_candidates)
    risk_assessment = _derive_risk_assessment(task_candidates, rejected_task_candidates)

    return {
        "_meta": {
            "purpose": "review_package",
            "generated_at": generated_at,
            "source_task_id": source_task_id,
        },
        "proposal": {
            "proposal_id": proposal_id,
            "block_id": block_id,
            "created_by": "generic_block_ai",
            "created_at": generated_at,
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "proposal_type": "task_review_package",
            "title": f"Task Review Package ({source_task_id})",
            "description": str(block_result.get("summary", "human review package")),
            "target_resource": "local_review_package",
            "proposed_action": "human_review",
            "estimated_impact": {
                "scope": scope,
                "reversible": True,
                "requires_human_approval": True,
                "auto_execute_allowed": False,
            },
        },
        "safety_constraints": {
            "publish_content": False,
            "delete_data": False,
            "change_config": False,
            "observe_only": True,
            "forbidden_actions_checked": True,
        },
        "review_requirements": {
            "requires_human_approval": True,
            "approver": approver,
            "approval_deadline": generated_at,
            "review_notes": "Review package generated from filtered task candidates",
        },
        "status": {
            "state": "pending_review",
            "last_updated": generated_at,
            "reviewer_decision": None,
            "rejection_reason": None,
        },
        "review_package": {
            "scope": scope,
            "non_goals": [
                "external writes",
                "production execution",
                "runtime policy mutation",
            ],
            "risk_assessment": risk_assessment,
            "guardrail_checks": {
                "production_status": "NO_GO",
                "operation_mode": "OBSERVE",
                "mode": "dry_run",
                "external_write_executed": False,
            },
            "rollback_conditions": [
                "any validator result == FAIL",
                "unexpected external_write_executed == true",
                "policy mismatch detected",
            ],
            "approval_required": True,
            "task_candidates": task_candidates,
            "rejected_task_candidates": rejected_task_candidates,
            "reason_codes": block_result.get("reason_codes", []),
            "review_required_fields": block_result.get("review_required_fields", []),
        },
    }


def write_review_package(
    *,
    base_path: Path,
    block_result: dict[str, Any],
    source_task_id: str,
    approver: str = "human_reviewer",
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_key = _safe_task_id(source_task_id)
    filename = f"review_package_{task_key}.json"
    path = reports_dir / filename

    package = build_review_package(
        block_result,
        source_task_id=source_task_id,
        approver=approver,
    )

    path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "package": package, "external_write_executed": False}
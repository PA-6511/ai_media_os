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


def build_signoff_audit_record(
    *,
    block_result: dict[str, Any],
    source_task_id: str,
    signoff_actor: str,
    human_signoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_decision = block_result.get("review_decision", {})
    quality_metrics = block_result.get("quality_metrics", {})
    policy_versioning = block_result.get("policy_versioning", {})

    signoff_payload = human_signoff if isinstance(human_signoff, dict) else {}

    return {
        "_meta": {
            "purpose": "signoff_audit",
            "generated_at": _utc_now_iso(),
            "source_task_id": source_task_id,
        },
        "signoff": {
            "actor": signoff_actor,
            "action": "recommended_decision_generated",
            "recommended_decision": review_decision.get("recommended_decision", "REQUIRE_HUMAN_REVIEW"),
            "reason": review_decision.get("reason", "requires_human_judgement"),
            "human_signoff": {
                "performed": bool(signoff_payload.get("performed", False)),
                "decision": signoff_payload.get("decision"),
                "comment": signoff_payload.get("comment"),
                "signed_at": signoff_payload.get("signed_at"),
            },
        },
        "decision_context": {
            "status": block_result.get("status"),
            "decision": block_result.get("decision"),
            "quality_metrics": {
                "quality_score": quality_metrics.get("quality_score"),
                "risk_balance": quality_metrics.get("risk_balance"),
                "review_readiness": quality_metrics.get("review_readiness"),
            },
            "policy": {
                "version": policy_versioning.get("version"),
                "environment": policy_versioning.get("environment"),
                "policy_hash": policy_versioning.get("policy_hash"),
            },
        },
        "safeguards": {
            "actual_auto_approve": False,
            "actual_auto_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }


def write_signoff_audit_log(
    *,
    base_path: Path,
    block_result: dict[str, Any],
    source_task_id: str,
    signoff_actor: str,
    human_signoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_key = _safe_task_id(source_task_id)
    path = reports_dir / f"signoff_audit_{task_key}.json"

    record = build_signoff_audit_record(
        block_result=block_result,
        source_task_id=source_task_id,
        signoff_actor=signoff_actor,
        human_signoff=human_signoff,
    )

    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "record": record,
        "external_write_executed": False,
    }
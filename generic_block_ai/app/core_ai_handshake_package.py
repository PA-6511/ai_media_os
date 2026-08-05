"""
core_ai_handshake_package.py — IR4-T1

generic_block_ai の実行結果を core_ai に渡せる decision_package 形式へ
変換します。外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HANDSHAKE_SCHEMA_VERSION = "handshake_v1"

REQUIRED_SAFETY_GATES: dict[str, Any] = {
    "connection_test_mode": True,
    "connection_scope": "decision_package_handoff_only",
    "operation_mode": "OBSERVE",
    "execution": "dry_run",
    "requires_human_approval": True,
    "auto_execute_allowed": False,
    "transport": "none",
    "external_api_call": False,
}


def _safe_task_id(source_task_id: str) -> str:
    normalized = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_"
        for ch in source_task_id.strip()
    )
    return normalized or "unknown_task"


def _derive_connection_status(block_result: dict[str, Any]) -> str:
    review_decision = block_result.get("review_decision", {})
    recommended = review_decision.get("recommended_decision", "")
    if recommended == "BLOCKED_BY_POLICY":
        return "HANDSHAKE_BLOCKED"
    if recommended == "RECOMMEND_REJECT":
        return "HANDSHAKE_REJECTED"
    if recommended == "RECOMMEND_APPROVE_DRY_RUN_ONLY":
        return "HANDSHAKE_READY_DRY_RUN"
    return "HANDSHAKE_PENDING_REVIEW"


def build_core_ai_handshake_package(
    block_result: dict[str, Any],
    *,
    source_task_id: str,
    block_id: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    task_key = _safe_task_id(source_task_id)
    resolved_block_id = block_id or str(block_result.get("meta", {}).get("block_id", "generic_block"))
    resolved_version = version or str(block_result.get("meta", {}).get("version", "unknown"))

    review_decision = block_result.get("review_decision", {})
    quality_metrics = block_result.get("quality_metrics", {})
    policy_versioning = block_result.get("policy_versioning", {})
    signoff_audit = block_result.get("signoff_audit", {})

    connection_status = _derive_connection_status(block_result)

    return {
        "_meta": {
            "schema_version": HANDSHAKE_SCHEMA_VERSION,
            "purpose": "core_ai_handshake",
            "generated_at": generated_at,
            "source_task_id": source_task_id,
            "source_block_id": resolved_block_id,
            "source_version": resolved_version,
        },
        "handshake_contract": {
            **REQUIRED_SAFETY_GATES,
        },
        "connection_status": connection_status,
        "source_summary": {
            "status": block_result.get("status"),
            "decision": block_result.get("decision"),
            "summary": block_result.get("summary", ""),
            "task_id": task_key,
        },
        "decision_package": {
            "recommended_decision": review_decision.get("recommended_decision", "REQUIRE_HUMAN_REVIEW"),
            "reason": review_decision.get("reason"),
            "quality_score": quality_metrics.get("quality_score"),
            "risk_balance": quality_metrics.get("risk_balance"),
            "review_readiness": quality_metrics.get("review_readiness"),
            "policy_version": policy_versioning.get("version"),
            "policy_hash": policy_versioning.get("policy_hash"),
            "signoff_actor": signoff_audit.get("record", {}).get("signoff", {}).get("actor"),
        },
        "validation_expectations": {
            "must_not_trigger_execution": True,
            "must_not_create_external_request": True,
            "must_not_change_runtime_mode": True,
            "must_preserve_no_go_status": True,
            "core_ai_expected_behavior": "observe_and_return_assessment_only",
        },
        "safeguards": {
            "actual_auto_approve": False,
            "actual_auto_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "requires_human_signoff": True,
        },
    }


def write_core_ai_handshake_package(
    *,
    base_path: Path,
    block_result: dict[str, Any],
    source_task_id: str,
    block_id: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_key = _safe_task_id(source_task_id)
    path = reports_dir / f"core_ai_handshake_{task_key}.json"

    package = build_core_ai_handshake_package(
        block_result,
        source_task_id=source_task_id,
        block_id=block_id,
        version=version,
    )
    path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "package": package, "external_write_executed": False}

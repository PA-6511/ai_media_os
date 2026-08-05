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


def _build_review_payload(
    block_result: dict[str, Any],
    *,
    source_task_id: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "decision": block_result.get("decision"),
        "summary": block_result.get("summary"),
        "needs_review_actions": block_result.get("needs_review_actions", []),
        "blocked_actions": block_result.get("blocked_actions", []),
        "reason_codes": block_result.get("reason_codes", []),
        "review_required_fields": block_result.get("review_required_fields", []),
        "generated_at": generated_at,
        "source_task_id": source_task_id,
        "block_id": block_result.get("meta", {}).get("block_id", "generic_block"),
        "production_status": "NO_GO",
        "external_write_executed": False,
    }


def build_review_queue_document(
    block_result: dict[str, Any],
    *,
    source_task_id: str,
    approver: str = "human_reviewer",
) -> dict[str, Any]:
    generated_at = _utc_now_iso()
    task_key = _safe_task_id(source_task_id)
    queue_id = f"hrq_{task_key}"
    entry_id = f"entry_{task_key}"
    proposal_id = f"proposal_{task_key}"

    review_payload = _build_review_payload(block_result, source_task_id=source_task_id, generated_at=generated_at)

    return {
        "_meta": {
            "purpose": "human_review_queue",
            "generated_at": generated_at,
            "source_task_id": source_task_id,
        },
        "queue_metadata": {
            "queue_id": queue_id,
            "block_id": review_payload["block_id"],
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "created_at": generated_at,
            "last_updated": generated_at,
            "auto_process_allowed": False,
            "requires_human_approval": True,
            "production_status": "NO_GO",
            "external_write_executed": False,
        },
        "queue_entries": [
            {
                "entry_id": entry_id,
                "proposal_id": proposal_id,
                "priority": "normal",
                "status": "pending_review",
                "submitted_at": generated_at,
                "reviewer": approver,
                "review_due": generated_at,
                "review_result": None,
                "notes": "IR1-T3 generated human review queue entry",
                "review_payload": review_payload,
            }
        ],
        "queue_policy": {
            "max_entries": 50,
            "auto_approve": False,
            "auto_reject_after_days": None,
            "escalation_enabled": False,
            "forbidden_auto_actions": [
                "auto_dequeue",
                "auto_execute",
                "auto_publish",
                "batch_approve_without_review",
            ],
        },
        "summary": {
            "total": 1,
            "pending_review": 1,
            "approved": 0,
            "rejected": 0,
            "expired": 0,
        },
    }


def build_evidence_index_document(
    block_result: dict[str, Any],
    *,
    source_task_id: str,
    review_queue_filename: str,
    evidence_filename: str,
) -> dict[str, Any]:
    generated_at = _utc_now_iso()
    task_key = _safe_task_id(source_task_id)
    index_id = f"hri_{task_key}"
    evidence_id = f"evidence_{task_key}"
    review_payload = _build_review_payload(block_result, source_task_id=source_task_id, generated_at=generated_at)

    return {
        "_meta": {
            "purpose": "human_review_evidence_index",
            "generated_at": generated_at,
            "source_task_id": source_task_id,
        },
        "index_metadata": {
            "index_id": index_id,
            "block_id": review_payload["block_id"],
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "created_at": generated_at,
            "last_updated": generated_at,
            "auto_export_allowed": False,
            "requires_human_approval": True,
            "production_status": "NO_GO",
            "external_write_executed": False,
        },
        "entries": [
            {
                "evidence_id": evidence_id,
                "phase": "implementation_restart_1",
                "filename": evidence_filename,
                "path": f"evidence/{evidence_filename}",
                "type": "decision_record",
                "created_at": generated_at,
                "checksum_sha256": "__PENDING__",
                "related_proposal_id": review_queue_filename,
                "status": "draft",
                "notes": "IR1-T3 generated evidence entry",
                "review_payload": review_payload,
            }
        ],
        "export_policy": {
            "auto_export": False,
            "allowed_destinations": [],
            "forbidden_actions": [
                "auto_upload_to_external",
                "overwrite_existing_evidence",
                "delete_evidence",
                "export_without_approval",
            ],
        },
        "summary": {
            "total_entries": 1,
            "draft": 1,
            "reviewed": 0,
            "archived": 0,
        },
    }


def write_human_review_artifacts(
    *,
    base_path: Path,
    block_result: dict[str, Any],
    source_task_id: str,
    approver: str = "human_reviewer",
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    evidence_dir = base_path / "evidence"
    reports_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    task_key = _safe_task_id(source_task_id)
    review_queue_filename = f"human_review_queue_{task_key}.json"
    evidence_filename = f"human_review_evidence_{task_key}.json"

    queue_doc = build_review_queue_document(
        block_result,
        source_task_id=source_task_id,
        approver=approver,
    )
    evidence_doc = build_evidence_index_document(
        block_result,
        source_task_id=source_task_id,
        review_queue_filename=review_queue_filename,
        evidence_filename=evidence_filename,
    )

    queue_path = reports_dir / review_queue_filename
    evidence_path = evidence_dir / evidence_filename

    queue_path.write_text(json.dumps(queue_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "review_queue_path": str(queue_path),
        "evidence_path": str(evidence_path),
        "review_queue": queue_doc,
        "evidence_index": evidence_doc,
        "external_write_executed": False,
    }
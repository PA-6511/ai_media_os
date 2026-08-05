from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence_index_validator import validate_evidence_index
from .review_queue_validator import validate_review_queue


REQUIRED_REVIEW_PAYLOAD_FIELDS = {
    "decision",
    "summary",
    "needs_review_actions",
    "blocked_actions",
    "reason_codes",
    "review_required_fields",
    "generated_at",
    "source_task_id",
    "block_id",
    "production_status",
    "external_write_executed",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def validate_review_artifacts_from_result(result: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failed: list[str] = []
    warnings: list[str] = []

    if result.get("decision") != "human_review":
        warnings.append("result.decision is not human_review; review_artifacts validation skipped")
        return {
            "overall_result": "WARN",
            "failed_checks": failed,
            "warnings": warnings,
            "checks": checks,
        }

    artifacts = result.get("review_artifacts")
    if not isinstance(artifacts, dict):
        failed.append("result.review_artifacts must be present for human_review decision")
        return {
            "overall_result": "FAIL",
            "failed_checks": failed,
            "warnings": warnings,
            "checks": checks,
        }

    queue_path_raw = str(artifacts.get("review_queue_path", "")).strip()
    evidence_path_raw = str(artifacts.get("evidence_path", "")).strip()
    external_write_executed = artifacts.get("external_write_executed")

    if not queue_path_raw:
        failed.append("review_artifacts.review_queue_path is required")
    if not evidence_path_raw:
        failed.append("review_artifacts.evidence_path is required")
    if external_write_executed is not False:
        failed.append("review_artifacts.external_write_executed must be false")

    if failed:
        return {
            "overall_result": "FAIL",
            "failed_checks": failed,
            "warnings": warnings,
            "checks": checks,
        }

    queue_path = Path(queue_path_raw)
    evidence_path = Path(evidence_path_raw)

    if not queue_path.exists():
        failed.append(f"review queue file does not exist: {queue_path}")
    if not evidence_path.exists():
        failed.append(f"evidence index file does not exist: {evidence_path}")

    if failed:
        return {
            "overall_result": "FAIL",
            "failed_checks": failed,
            "warnings": warnings,
            "checks": checks,
        }

    queue_doc = _load_json(queue_path)
    evidence_doc = _load_json(evidence_path)

    queue_validation = validate_review_queue(queue_doc)
    evidence_validation = validate_evidence_index(evidence_doc)

    checks.append(
        {
            "target": str(queue_path),
            "validator": "review_queue_validator",
            "result": queue_validation.result,
            "failed_checks": queue_validation.failed_checks,
            "warnings": queue_validation.warnings,
        }
    )
    checks.append(
        {
            "target": str(evidence_path),
            "validator": "evidence_index_validator",
            "result": evidence_validation.result,
            "failed_checks": evidence_validation.failed_checks,
            "warnings": evidence_validation.warnings,
        }
    )

    if queue_validation.result == "FAIL":
        failed.append("review queue validation failed")
    if evidence_validation.result == "FAIL":
        failed.append("evidence index validation failed")

    queue_entries = queue_doc.get("queue_entries", [])
    if queue_entries:
        review_payload = queue_entries[0].get("review_payload", {})
        missing = sorted(REQUIRED_REVIEW_PAYLOAD_FIELDS - set(review_payload.keys()))
        if missing:
            failed.append(f"review_payload is missing required fields: {missing}")

    if failed:
        overall = "FAIL"
    elif queue_validation.result == "WARN" or evidence_validation.result == "WARN":
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "overall_result": overall,
        "failed_checks": failed,
        "warnings": warnings,
        "checks": checks,
    }


def write_review_artifacts_summary(
    *,
    base_path: Path,
    source_task_id: str,
    validation_result: dict[str, Any],
) -> dict[str, str]:
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in source_task_id) or "unknown"
    json_path = reports_dir / f"human_review_artifacts_summary_{task_key}.json"
    md_path = reports_dir / f"human_review_artifacts_summary_{task_key}.md"

    payload = {
        "_meta": {
            "purpose": "human_review_artifacts_summary",
            "generated_at": _utc_now_iso(),
            "source_task_id": source_task_id,
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "auto_execute_allowed": False,
            "requires_human_approval": True,
        },
        **validation_result,
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Human Review Artifacts Summary",
        "",
        f"- source_task_id: {source_task_id}",
        f"- overall_result: {validation_result.get('overall_result')}",
        f"- generated_at: {payload['_meta']['generated_at']}",
        "",
        "## Failed Checks",
    ]

    failed_checks = validation_result.get("failed_checks", [])
    if failed_checks:
        lines.extend([f"- {item}" for item in failed_checks])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = validation_result.get("warnings", [])
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    lines.extend(["", "## Checks"])
    for item in validation_result.get("checks", []):
        lines.append(f"- {item.get('validator')}: {item.get('result')} ({item.get('target')})")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "summary_json_path": str(json_path),
        "summary_md_path": str(md_path),
    }
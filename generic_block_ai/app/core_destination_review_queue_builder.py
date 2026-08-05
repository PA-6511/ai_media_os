"""
core_destination_review_queue_builder.py - IR45

Build destination review queues from IR44 submission gate decisions in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR44_SCHEMA_VERSION = "ir44_destination_evidence_bundle_submission_gate_v1"
IR45_SCHEMA_VERSION = "ir45_destination_review_queue_builder_v1"

DECISION_READY_FOR_REVIEW = "READY_FOR_REVIEW"
DECISION_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"

QUEUE_QUEUED = "QUEUED_FOR_REVIEW"
QUEUE_HOLD = "HOLD_FOR_HUMAN_REVIEW"
QUEUE_REJECTED = "REJECTED_NO_QUEUE"
QUEUE_ABORTED = "ABORTED_NO_QUEUE"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _queue_status(decision: str) -> str:
    if decision == DECISION_READY_FOR_REVIEW:
        return QUEUE_QUEUED
    if decision == DECISION_HUMAN_REVIEW_REQUIRED:
        return QUEUE_HOLD
    if decision == DECISION_REJECT:
        return QUEUE_REJECTED
    return QUEUE_ABORTED


def _review_items(decision: str, destination: str) -> list[dict[str, Any]]:
    if decision == DECISION_READY_FOR_REVIEW:
        return [
            {
                "item_id": f"{destination}-R1",
                "title": "Verify hash manifest and summary link consistency",
                "owner_role": "destination_reviewer",
                "required": True,
            },
            {
                "item_id": f"{destination}-R2",
                "title": "Confirm evidence digest and bundle hash correspondence",
                "owner_role": "integrity_reviewer",
                "required": True,
            },
        ]
    if decision == DECISION_HUMAN_REVIEW_REQUIRED:
        return [
            {
                "item_id": f"{destination}-H1",
                "title": "Perform manual reconciliation for recompute mismatch",
                "owner_role": "human_reviewer",
                "required": True,
            }
        ]
    if decision == DECISION_REJECT:
        return [
            {
                "item_id": f"{destination}-J1",
                "title": "Reject and return bundle for evidence correction",
                "owner_role": "submission_owner",
                "required": True,
            }
        ]
    return [
        {
            "item_id": f"{destination}-A1",
            "title": "Escalate abort due to critical artifact absence",
            "owner_role": "incident_commander",
            "required": True,
        }
    ]


def run_ir45_destination_review_queue_builder_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir44_submission_gate_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR45-T1/T2/T3/T4
    Build destination review queue from IR44 submission gate report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir44_path = ir44_submission_gate_report_path or (
        reports_dir / "ir44_destination_evidence_bundle_submission_gate_report_ir44_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_review_queue: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"

    if not ir44_path.exists():
        failed_checks.append(f"ir44 submission gate report not found: {ir44_path}")

    ir44_report: dict[str, Any] = {}
    if not failed_checks:
        ir44_report = _read_json(ir44_path)
        if ir44_report.get("schema_version") != IR44_SCHEMA_VERSION:
            failed_checks.append(f"ir44 schema_version must be {IR44_SCHEMA_VERSION}")

        release_candidate_id = str(ir44_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir44_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir44_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir44_report.get("overall_submission_gate_decision", "UNKNOWN"))

    rows = ir44_report.get("destination_submission_gate", [])
    if not isinstance(rows, list):
        failed_checks.append("ir44 destination_submission_gate must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir44 destination_submission_gate entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision = str(row.get("submission_gate_decision", "UNKNOWN"))
        queue_status = _queue_status(decision)
        items = _review_items(decision, destination)

        checklist = [
            "Confirm hash manifest path is reachable.",
            "Confirm review summary reflects gate decision.",
            "Confirm evidence digest and bundle hash references are attached.",
        ]
        if decision != DECISION_READY_FOR_REVIEW:
            checklist.append("Escalate to designated owner before queue progression.")

        destination_review_queue.append(
            {
                "destination": destination,
                "submission_gate_decision": decision,
                "review_queue_status": queue_status,
                "review_items": items,
                "owner_checklist": checklist,
                "evidence_reference_links": {
                    "hash_manifest": str(row.get("hash_manifest_path", "")),
                    "review_summary": str(row.get("review_summary_path", "")),
                    "gate_report": _to_ref(ir44_path, project_root),
                },
                "gate_reasons": [str(v) for v in row.get("gate_reasons", [])],
            }
        )

    queued_count = sum(1 for d in destination_review_queue if d["review_queue_status"] == QUEUE_QUEUED)
    hold_count = sum(1 for d in destination_review_queue if d["review_queue_status"] == QUEUE_HOLD)
    rejected_count = sum(1 for d in destination_review_queue if d["review_queue_status"] == QUEUE_REJECTED)
    aborted_count = sum(1 for d in destination_review_queue if d["review_queue_status"] == QUEUE_ABORTED)

    if overall_submission_gate_decision == "UNKNOWN":
        failed_checks.append("overall_submission_gate_decision is missing or unknown")

    overall_queue_action = {
        DECISION_READY_FOR_REVIEW: "Build review queue entries and hand off to destination reviewers.",
        DECISION_HUMAN_REVIEW_REQUIRED: "Hold queue progression and request manual review first.",
        DECISION_REJECT: "Reject queue entries and return to evidence correction workflow.",
        DECISION_ABORT: "Abort queue construction and escalate incident workflow.",
    }.get(overall_submission_gate_decision, "Unknown gate decision; keep queue in safe hold.")

    queue_root = reports_dir / f"ir45_destination_review_queue_builder_{_safe(source_task_id)}"
    queue_root.mkdir(parents=True, exist_ok=True)

    queue_json_path = queue_root / "destination_review_queue.json"
    summary_md_path = queue_root / "destination_review_queue_summary.md"

    report = {
        "schema_version": IR45_SCHEMA_VERSION,
        "phase": "IR45",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_queue_action": overall_queue_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_review_queue),
            "queued_for_review_count": queued_count,
            "hold_for_human_review_count": hold_count,
            "rejected_no_queue_count": rejected_count,
            "aborted_no_queue_count": aborted_count,
            "review_item_count": sum(len(d.get("review_items", [])) for d in destination_review_queue),
        },
        "destination_review_queue": destination_review_queue,
        "artifacts": {
            "queue_root": _to_ref(queue_root, project_root),
            "destination_review_queue": _to_ref(queue_json_path, project_root),
            "destination_review_queue_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase45_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    queue_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Review Queue Builder",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Submission Gate Decision: {overall_submission_gate_decision}",
        f"- Overall Queue Action: {overall_queue_action}",
        "",
        "## Destination Queue Status",
    ]
    for row in destination_review_queue:
        summary_lines.append(f"- {row['destination']} -> {row['review_queue_status']}")
        for item in row.get("review_items", []):
            summary_lines.append(f"  - {item['item_id']}: {item['title']}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir45_destination_review_queue_builder_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir45_completion_report(
    *,
    base_path: Path,
    ir45_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR45-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir45_output.get("runbook_report", {}) if isinstance(ir45_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 45",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR45_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir43_ir45": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_queue_action": runbook.get("overall_queue_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir45_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase45_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase45_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
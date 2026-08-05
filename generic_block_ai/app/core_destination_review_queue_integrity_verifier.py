"""
core_destination_review_queue_integrity_verifier.py - IR46

Verify destination review queue integrity from IR45 outputs in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR45_SCHEMA_VERSION = "ir45_destination_review_queue_builder_v1"
IR46_SCHEMA_VERSION = "ir46_destination_review_queue_integrity_verifier_v1"

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


def _resolve_report_path(raw_path: str, project_root: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return project_root / path


def _expected_item_count(queue_status: str) -> int:
    if queue_status == QUEUE_QUEUED:
        return 2
    return 1


def run_ir46_destination_review_queue_integrity_verifier_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir45_review_queue_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR46-T1/T2/T3/T4
    Verify queue item integrity from IR45 destination review queue report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir45_path = ir45_review_queue_report_path or (
        reports_dir / "ir45_destination_review_queue_builder_report_ir45_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_integrity_results: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"

    if not ir45_path.exists():
        failed_checks.append(f"ir45 review queue report not found: {ir45_path}")

    ir45_report: dict[str, Any] = {}
    if not failed_checks:
        ir45_report = _read_json(ir45_path)
        if ir45_report.get("schema_version") != IR45_SCHEMA_VERSION:
            failed_checks.append(f"ir45 schema_version must be {IR45_SCHEMA_VERSION}")

        release_candidate_id = str(ir45_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir45_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir45_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir45_report.get("overall_submission_gate_decision", "UNKNOWN"))

    rows = ir45_report.get("destination_review_queue", [])
    if not isinstance(rows, list):
        failed_checks.append("ir45 destination_review_queue must be list")
        rows = []

    seen_destinations: set[str] = set()
    seen_item_ids: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir45 destination_review_queue entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        queue_status = str(row.get("review_queue_status", "UNKNOWN"))
        items = row.get("review_items", []) if isinstance(row.get("review_items"), list) else []
        checklist = row.get("owner_checklist", []) if isinstance(row.get("owner_checklist"), list) else []
        links = row.get("evidence_reference_links", {}) if isinstance(row.get("evidence_reference_links"), dict) else {}

        failed_reasons: list[str] = []

        duplicate_destination = destination in seen_destinations
        seen_destinations.add(destination)

        item_ids = [str(i.get("item_id", "")) for i in items if isinstance(i, dict)]
        duplicate_item_ids = len(item_ids) != len(set(item_ids))

        cross_destination_item_dup = False
        for item_id in item_ids:
            if item_id in seen_item_ids:
                cross_destination_item_dup = True
            seen_item_ids.add(item_id)

        missing_items = len(items) == 0
        item_count_ok = len(items) == _expected_item_count(queue_status)
        checklist_ok = len(checklist) >= 3

        hash_manifest_path = _resolve_report_path(str(links.get("hash_manifest", "")), project_root)
        review_summary_path = _resolve_report_path(str(links.get("review_summary", "")), project_root)
        gate_report_path = _resolve_report_path(str(links.get("gate_report", "")), project_root)

        evidence_links_ok = hash_manifest_path.exists() and review_summary_path.exists() and gate_report_path.exists()

        queue_status_ok = queue_status in {QUEUE_QUEUED, QUEUE_HOLD, QUEUE_REJECTED, QUEUE_ABORTED}
        if not queue_status_ok:
            failed_reasons.append("unknown review_queue_status")
        if duplicate_destination:
            failed_reasons.append("duplicate destination entry detected")
        if missing_items:
            failed_reasons.append("review_items missing")
        if duplicate_item_ids or cross_destination_item_dup:
            failed_reasons.append("duplicate review item id detected")
        if not item_count_ok:
            failed_reasons.append("review item count mismatch for queue status")
        if not checklist_ok:
            failed_reasons.append("owner checklist is incomplete")
        if not evidence_links_ok:
            failed_reasons.append("evidence reference link missing or unresolved")

        destination_integrity_results.append(
            {
                "destination": destination,
                "review_queue_status": queue_status,
                "integrity_result": "PASS" if not failed_reasons else "FAIL",
                "integrity_checks": {
                    "queue_status_ok": queue_status_ok,
                    "missing_items": missing_items,
                    "duplicate_destination": duplicate_destination,
                    "duplicate_item_ids": duplicate_item_ids or cross_destination_item_dup,
                    "item_count_ok": item_count_ok,
                    "checklist_ok": checklist_ok,
                    "evidence_links_ok": evidence_links_ok,
                },
                "review_item_ids": item_ids,
                "failed_reasons": failed_reasons,
                "evidence_reference_links": {
                    "hash_manifest": _to_ref(hash_manifest_path, project_root),
                    "review_summary": _to_ref(review_summary_path, project_root),
                    "gate_report": _to_ref(gate_report_path, project_root),
                },
            }
        )

    pass_count = sum(1 for d in destination_integrity_results if d["integrity_result"] == "PASS")
    fail_count = sum(1 for d in destination_integrity_results if d["integrity_result"] == "FAIL")

    if overall_submission_gate_decision == "UNKNOWN":
        failed_checks.append("overall_submission_gate_decision is missing or unknown")
    if fail_count > 0:
        failed_checks.append(f"destination queue integrity failures detected: {fail_count}")

    if fail_count == 0 and destination_integrity_results:
        overall_integrity_action = "Review queue integrity verified for item completeness, uniqueness, links, and status mapping."
    elif destination_integrity_results:
        overall_integrity_action = "Review queue integrity issues detected; hold progression and require remediation."
    else:
        overall_integrity_action = "No destination review queue entries available for integrity verification."

    verifier_root = reports_dir / f"ir46_destination_review_queue_integrity_verifier_{_safe(source_task_id)}"
    verifier_root.mkdir(parents=True, exist_ok=True)

    verifier_json_path = verifier_root / "destination_review_queue_integrity_verifier.json"
    summary_md_path = verifier_root / "destination_review_queue_integrity_summary.md"

    report = {
        "schema_version": IR46_SCHEMA_VERSION,
        "phase": "IR46",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_integrity_action": overall_integrity_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_integrity_results),
            "integrity_pass_count": pass_count,
            "integrity_fail_count": fail_count,
            "queue_status_verified_count": sum(1 for d in destination_integrity_results if d["integrity_checks"]["queue_status_ok"]),
            "item_uniqueness_verified_count": sum(1 for d in destination_integrity_results if not d["integrity_checks"]["duplicate_item_ids"]),
            "evidence_link_verified_count": sum(1 for d in destination_integrity_results if d["integrity_checks"]["evidence_links_ok"]),
        },
        "destination_review_queue_integrity": destination_integrity_results,
        "artifacts": {
            "verifier_root": _to_ref(verifier_root, project_root),
            "destination_review_queue_integrity_verifier": _to_ref(verifier_json_path, project_root),
            "destination_review_queue_integrity_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase46_completion_report.json",
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

    verifier_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Review Queue Integrity Verifier",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Submission Gate Decision: {overall_submission_gate_decision}",
        f"- Overall Integrity Action: {overall_integrity_action}",
        "",
        "## Destination Integrity Results",
    ]
    for row in destination_integrity_results:
        summary_lines.append(f"- {row['destination']} -> {row['integrity_result']}")
        for reason in row.get("failed_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir46_destination_review_queue_integrity_verifier_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir46_completion_report(
    *,
    base_path: Path,
    ir46_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR46-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir46_output.get("runbook_report", {}) if isinstance(ir46_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 46",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR46_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir44_ir46": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_integrity_action": runbook.get("overall_integrity_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir46_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase46_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase46_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
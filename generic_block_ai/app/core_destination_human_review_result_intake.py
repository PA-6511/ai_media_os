"""
core_destination_human_review_result_intake.py - IR48

Intake destination human review results from IR47 approval gate in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR47_SCHEMA_VERSION = "ir47_destination_review_queue_approval_gate_v1"
IR48_SCHEMA_VERSION = "ir48_destination_human_review_result_intake_v1"

APPROVAL_READY = "READY_FOR_HUMAN_REVIEW"
APPROVAL_HOLD = "HOLD"
APPROVAL_REJECT = "REJECT"
APPROVAL_ABORT = "ABORT"

REVIEW_APPROVE = "APPROVE"
REVIEW_REQUEST_FIX = "REQUEST_FIX"
REVIEW_REJECT = "REJECT"
REVIEW_ABORT_ACK = "ABORT_ACK"


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


def _review_result(row: dict[str, Any]) -> tuple[str, str, list[str]]:
    approval_decision = str(row.get("review_queue_approval_decision", "UNKNOWN"))
    integrity_result = str(row.get("integrity_result", "UNKNOWN"))
    reasons = [str(v) for v in row.get("approval_reasons", [])]

    if approval_decision == APPROVAL_READY and integrity_result == "PASS":
        return REVIEW_APPROVE, "human_queue_reviewer", ["queue approved for human review intake"]
    if approval_decision == APPROVAL_HOLD:
        return REVIEW_REQUEST_FIX, "human_queue_reviewer", reasons or ["request remediation before approval"]
    if approval_decision == APPROVAL_REJECT:
        return REVIEW_REJECT, "review_governance_owner", reasons or ["review queue rejected"]
    return REVIEW_ABORT_ACK, "incident_commander", reasons or ["abort acknowledged by review intake"]


def _overall_review_result(results: list[str]) -> str:
    if REVIEW_ABORT_ACK in results:
        return REVIEW_ABORT_ACK
    if REVIEW_REJECT in results:
        return REVIEW_REJECT
    if REVIEW_REQUEST_FIX in results:
        return REVIEW_REQUEST_FIX
    return REVIEW_APPROVE


def run_ir48_destination_human_review_result_intake_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir47_approval_gate_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR48-T1/T2/T3/T4
    Convert IR47 approval gate decisions into destination human review intake records.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir47_path = ir47_approval_gate_report_path or (
        reports_dir / "ir47_destination_review_queue_approval_gate_report_ir47_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_human_review_results: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"
    overall_review_queue_approval_decision = "UNKNOWN"

    if not ir47_path.exists():
        failed_checks.append(f"ir47 approval gate report not found: {ir47_path}")

    ir47_report: dict[str, Any] = {}
    if not failed_checks:
        ir47_report = _read_json(ir47_path)
        if ir47_report.get("schema_version") != IR47_SCHEMA_VERSION:
            failed_checks.append(f"ir47 schema_version must be {IR47_SCHEMA_VERSION}")

        release_candidate_id = str(ir47_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir47_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir47_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir47_report.get("overall_submission_gate_decision", "UNKNOWN"))
        overall_review_queue_approval_decision = str(
            ir47_report.get("overall_review_queue_approval_decision", "UNKNOWN")
        )

    rows = ir47_report.get("destination_review_queue_approval_gate", [])
    if not isinstance(rows, list):
        failed_checks.append("ir47 destination_review_queue_approval_gate must be list")
        rows = []

    intake_root = reports_dir / f"ir48_destination_human_review_result_intake_{_safe(source_task_id)}"
    intake_root.mkdir(parents=True, exist_ok=True)

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir47 destination_review_queue_approval_gate entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        review_result, reviewer_role, review_notes = _review_result(row)
        intake_record_path = intake_root / f"{_safe(destination)}_human_review_result.json"

        intake_record = {
            "destination": destination,
            "review_queue_approval_decision": str(row.get("review_queue_approval_decision", "UNKNOWN")),
            "human_review_result": review_result,
            "reviewer_role": reviewer_role,
            "integrity_result": str(row.get("integrity_result", "UNKNOWN")),
            "review_item_ids": [str(v) for v in row.get("review_item_ids", [])],
            "review_notes": review_notes,
            "evidence_reference_links": row.get("evidence_reference_links", {}),
            "recorded_at": _now_iso(),
        }
        intake_record_path.write_text(json.dumps(intake_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        destination_human_review_results.append(
            {
                **intake_record,
                "approval_reasons": [str(v) for v in row.get("approval_reasons", [])],
                "intake_record_path": _to_ref(intake_record_path, project_root),
            }
        )

    results = [r["human_review_result"] for r in destination_human_review_results]
    overall_human_review_result = _overall_review_result(results)

    approve_count = sum(1 for r in results if r == REVIEW_APPROVE)
    request_fix_count = sum(1 for r in results if r == REVIEW_REQUEST_FIX)
    reject_count = sum(1 for r in results if r == REVIEW_REJECT)
    abort_ack_count = sum(1 for r in results if r == REVIEW_ABORT_ACK)

    if overall_review_queue_approval_decision == "UNKNOWN":
        failed_checks.append("overall_review_queue_approval_decision is missing or unknown")

    if overall_human_review_result == REVIEW_APPROVE:
        overall_intake_action = "Human review intake recorded destination approvals."
    elif overall_human_review_result == REVIEW_REQUEST_FIX:
        overall_intake_action = "Human review intake recorded remediation requests."
    elif overall_human_review_result == REVIEW_REJECT:
        overall_intake_action = "Human review intake recorded rejection outcomes."
    else:
        overall_intake_action = "Human review intake recorded abort acknowledgements."

    intake_json_path = intake_root / "destination_human_review_result_intake.json"
    summary_md_path = intake_root / "destination_human_review_result_intake_summary.md"

    report = {
        "schema_version": IR48_SCHEMA_VERSION,
        "phase": "IR48",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_review_queue_approval_decision": overall_review_queue_approval_decision,
        "overall_human_review_result": overall_human_review_result,
        "overall_intake_action": overall_intake_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_human_review_results),
            "approve_count": approve_count,
            "request_fix_count": request_fix_count,
            "reject_count": reject_count,
            "abort_ack_count": abort_ack_count,
        },
        "destination_human_review_result_intake": destination_human_review_results,
        "artifacts": {
            "intake_root": _to_ref(intake_root, project_root),
            "destination_human_review_result_intake": _to_ref(intake_json_path, project_root),
            "destination_human_review_result_intake_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase48_completion_report.json",
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

    intake_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Human Review Result Intake",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Human Review Result: {overall_human_review_result}",
        f"- Overall Intake Action: {overall_intake_action}",
        "",
        "## Destination Review Intake Results",
    ]
    for row in destination_human_review_results:
        summary_lines.append(f"- {row['destination']} -> {row['human_review_result']}")
        for note in row.get("review_notes", []):
            summary_lines.append(f"  - {note}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir48_destination_human_review_result_intake_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir48_completion_report(
    *,
    base_path: Path,
    ir48_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR48-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir48_output.get("runbook_report", {}) if isinstance(ir48_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 48",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR48_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir46_ir48": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_review_queue_approval_decision": runbook.get("overall_review_queue_approval_decision", "UNKNOWN"),
        "overall_human_review_result": runbook.get("overall_human_review_result", "UNKNOWN"),
        "overall_intake_action": runbook.get("overall_intake_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir48_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase48_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase48_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
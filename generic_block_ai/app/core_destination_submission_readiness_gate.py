"""
core_destination_submission_readiness_gate.py - IR49

Gate destination submission readiness from IR48 human review intake in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR48_SCHEMA_VERSION = "ir48_destination_human_review_result_intake_v1"
IR49_SCHEMA_VERSION = "ir49_destination_submission_readiness_gate_v1"

REVIEW_APPROVE = "APPROVE"
REVIEW_REQUEST_FIX = "REQUEST_FIX"
REVIEW_REJECT = "REJECT"
REVIEW_ABORT_ACK = "ABORT_ACK"

READINESS_READY = "READY_DRY_RUN_ONLY"
READINESS_HOLD = "HOLD"
READINESS_REJECT = "REJECT"
READINESS_ABORT = "ABORT"


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


def _readiness_decision(row: dict[str, Any]) -> tuple[str, list[str]]:
    human_review_result = str(row.get("human_review_result", "UNKNOWN"))
    review_notes = [str(v) for v in row.get("review_notes", [])]

    if human_review_result == REVIEW_APPROVE:
        return READINESS_READY, ["human review approved destination for dry-run submission readiness"]
    if human_review_result == REVIEW_REQUEST_FIX:
        return READINESS_HOLD, review_notes or ["submission readiness held for requested fixes"]
    if human_review_result == REVIEW_REJECT:
        return READINESS_REJECT, review_notes or ["submission readiness rejected by human review"]
    return READINESS_ABORT, review_notes or ["submission readiness aborted after abort acknowledgement"]


def _overall_readiness(decisions: list[str]) -> str:
    if READINESS_ABORT in decisions:
        return READINESS_ABORT
    if READINESS_REJECT in decisions:
        return READINESS_REJECT
    if READINESS_HOLD in decisions:
        return READINESS_HOLD
    return READINESS_READY


def run_ir49_destination_submission_readiness_gate_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir48_human_review_result_intake_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR49-T1/T2/T3/T4
    Convert IR48 human review intake outputs into destination submission readiness decisions.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir48_path = ir48_human_review_result_intake_report_path or (
        reports_dir / "ir48_destination_human_review_result_intake_report_ir48_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_submission_readiness: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"
    overall_review_queue_approval_decision = "UNKNOWN"
    overall_human_review_result = "UNKNOWN"

    if not ir48_path.exists():
        failed_checks.append(f"ir48 human review intake report not found: {ir48_path}")

    ir48_report: dict[str, Any] = {}
    if not failed_checks:
        ir48_report = _read_json(ir48_path)
        if ir48_report.get("schema_version") != IR48_SCHEMA_VERSION:
            failed_checks.append(f"ir48 schema_version must be {IR48_SCHEMA_VERSION}")

        release_candidate_id = str(ir48_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir48_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir48_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir48_report.get("overall_submission_gate_decision", "UNKNOWN"))
        overall_review_queue_approval_decision = str(
            ir48_report.get("overall_review_queue_approval_decision", "UNKNOWN")
        )
        overall_human_review_result = str(ir48_report.get("overall_human_review_result", "UNKNOWN"))

    rows = ir48_report.get("destination_human_review_result_intake", [])
    if not isinstance(rows, list):
        failed_checks.append("ir48 destination_human_review_result_intake must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir48 destination_human_review_result_intake entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        readiness_decision, readiness_reasons = _readiness_decision(row)
        destination_submission_readiness.append(
            {
                "destination": destination,
                "submission_readiness_decision": readiness_decision,
                "readiness_reasons": readiness_reasons,
                "human_review_result": str(row.get("human_review_result", "UNKNOWN")),
                "reviewer_role": str(row.get("reviewer_role", "UNKNOWN")),
                "review_item_ids": [str(v) for v in row.get("review_item_ids", [])],
                "review_notes": [str(v) for v in row.get("review_notes", [])],
                "intake_record_path": str(row.get("intake_record_path", "")),
                "evidence_reference_links": row.get("evidence_reference_links", {}),
            }
        )

    decisions = [r["submission_readiness_decision"] for r in destination_submission_readiness]
    overall_submission_readiness_decision = _overall_readiness(decisions)

    ready_count = sum(1 for d in decisions if d == READINESS_READY)
    hold_count = sum(1 for d in decisions if d == READINESS_HOLD)
    reject_count = sum(1 for d in decisions if d == READINESS_REJECT)
    abort_count = sum(1 for d in decisions if d == READINESS_ABORT)

    if overall_human_review_result == "UNKNOWN":
        failed_checks.append("overall_human_review_result is missing or unknown")

    if overall_submission_readiness_decision == READINESS_READY:
        overall_gate_action = "Approved destinations are ready for dry-run submission progression."
    elif overall_submission_readiness_decision == READINESS_HOLD:
        overall_gate_action = "Hold submission readiness until requested fixes are resolved."
    elif overall_submission_readiness_decision == READINESS_REJECT:
        overall_gate_action = "Reject submission readiness and route back to review correction."
    else:
        overall_gate_action = "Abort submission readiness due to acknowledged abort conditions."

    gate_root = reports_dir / f"ir49_destination_submission_readiness_gate_{_safe(source_task_id)}"
    gate_root.mkdir(parents=True, exist_ok=True)

    gate_json_path = gate_root / "destination_submission_readiness_gate.json"
    summary_md_path = gate_root / "destination_submission_readiness_gate_summary.md"

    report = {
        "schema_version": IR49_SCHEMA_VERSION,
        "phase": "IR49",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_review_queue_approval_decision": overall_review_queue_approval_decision,
        "overall_human_review_result": overall_human_review_result,
        "overall_submission_readiness_decision": overall_submission_readiness_decision,
        "overall_gate_action": overall_gate_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_submission_readiness),
            "ready_dry_run_only_count": ready_count,
            "hold_count": hold_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
        },
        "destination_submission_readiness": destination_submission_readiness,
        "artifacts": {
            "gate_root": _to_ref(gate_root, project_root),
            "destination_submission_readiness_gate": _to_ref(gate_json_path, project_root),
            "destination_submission_readiness_gate_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase49_completion_report.json",
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

    gate_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Submission Readiness Gate",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Submission Readiness Decision: {overall_submission_readiness_decision}",
        f"- Overall Gate Action: {overall_gate_action}",
        "",
        "## Destination Submission Readiness",
    ]
    for row in destination_submission_readiness:
        summary_lines.append(f"- {row['destination']} -> {row['submission_readiness_decision']}")
        for reason in row.get("readiness_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir49_destination_submission_readiness_gate_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir49_completion_report(
    *,
    base_path: Path,
    ir49_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR49-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir49_output.get("runbook_report", {}) if isinstance(ir49_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 49",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR49_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir47_ir49": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_review_queue_approval_decision": runbook.get("overall_review_queue_approval_decision", "UNKNOWN"),
        "overall_human_review_result": runbook.get("overall_human_review_result", "UNKNOWN"),
        "overall_submission_readiness_decision": runbook.get("overall_submission_readiness_decision", "UNKNOWN"),
        "overall_gate_action": runbook.get("overall_gate_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir49_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase49_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase49_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
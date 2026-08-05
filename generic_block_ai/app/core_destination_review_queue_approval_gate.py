"""
core_destination_review_queue_approval_gate.py - IR47

Gate destination review queue approvals from IR46 integrity verifier in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR46_SCHEMA_VERSION = "ir46_destination_review_queue_integrity_verifier_v1"
IR47_SCHEMA_VERSION = "ir47_destination_review_queue_approval_gate_v1"

QUEUE_QUEUED = "QUEUED_FOR_REVIEW"
QUEUE_HOLD = "HOLD_FOR_HUMAN_REVIEW"
QUEUE_REJECTED = "REJECTED_NO_QUEUE"
QUEUE_ABORTED = "ABORTED_NO_QUEUE"

APPROVAL_READY = "READY_FOR_HUMAN_REVIEW"
APPROVAL_HOLD = "HOLD"
APPROVAL_REJECT = "REJECT"
APPROVAL_ABORT = "ABORT"


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


def _destination_approval(row: dict[str, Any]) -> tuple[str, list[str]]:
    queue_status = str(row.get("review_queue_status", "UNKNOWN"))
    integrity_result = str(row.get("integrity_result", "UNKNOWN"))
    failed_reasons = [str(v) for v in row.get("failed_reasons", [])]

    reasons: list[str] = []

    if integrity_result != "PASS":
        if queue_status == QUEUE_ABORTED or any(
            key in " ".join(failed_reasons).lower() for key in ["missing", "unknown", "unresolved"]
        ):
            reasons.append("critical integrity issue detected; abort required")
            return APPROVAL_ABORT, reasons
        if queue_status == QUEUE_REJECTED:
            reasons.append("integrity failed and queue already rejected")
            return APPROVAL_REJECT, reasons
        reasons.append("integrity failed; hold for remediation before review")
        return APPROVAL_HOLD, reasons

    if queue_status == QUEUE_QUEUED:
        reasons.append("integrity passed and queue ready for human review")
        return APPROVAL_READY, reasons
    if queue_status == QUEUE_HOLD:
        reasons.append("queue is intentionally held for human review preparation")
        return APPROVAL_HOLD, reasons
    if queue_status == QUEUE_REJECTED:
        reasons.append("queue status indicates rejection path")
        return APPROVAL_REJECT, reasons
    if queue_status == QUEUE_ABORTED:
        reasons.append("queue status indicates abort path")
        return APPROVAL_ABORT, reasons

    reasons.append("unknown queue status; safe abort")
    return APPROVAL_ABORT, reasons


def _overall_approval(decisions: list[str]) -> str:
    if APPROVAL_ABORT in decisions:
        return APPROVAL_ABORT
    if APPROVAL_REJECT in decisions:
        return APPROVAL_REJECT
    if APPROVAL_HOLD in decisions:
        return APPROVAL_HOLD
    return APPROVAL_READY


def run_ir47_destination_review_queue_approval_gate_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir46_integrity_verifier_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR47-T1/T2/T3/T4
    Convert IR46 integrity verifier outputs into destination review queue approval gate decisions.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir46_path = ir46_integrity_verifier_report_path or (
        reports_dir / "ir46_destination_review_queue_integrity_verifier_report_ir46_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_approval_gate: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"

    if not ir46_path.exists():
        failed_checks.append(f"ir46 integrity verifier report not found: {ir46_path}")

    ir46_report: dict[str, Any] = {}
    if not failed_checks:
        ir46_report = _read_json(ir46_path)
        if ir46_report.get("schema_version") != IR46_SCHEMA_VERSION:
            failed_checks.append(f"ir46 schema_version must be {IR46_SCHEMA_VERSION}")

        release_candidate_id = str(ir46_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir46_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir46_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir46_report.get("overall_submission_gate_decision", "UNKNOWN"))

    rows = ir46_report.get("destination_review_queue_integrity", [])
    if not isinstance(rows, list):
        failed_checks.append("ir46 destination_review_queue_integrity must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir46 destination_review_queue_integrity entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision, reasons = _destination_approval(row)
        destination_approval_gate.append(
            {
                "destination": destination,
                "review_queue_approval_decision": decision,
                "approval_reasons": reasons,
                "review_queue_status": str(row.get("review_queue_status", "UNKNOWN")),
                "integrity_result": str(row.get("integrity_result", "UNKNOWN")),
                "integrity_checks": row.get("integrity_checks", {}),
                "review_item_ids": row.get("review_item_ids", []),
                "integrity_failed_reasons": [str(v) for v in row.get("failed_reasons", [])],
                "evidence_reference_links": row.get("evidence_reference_links", {}),
            }
        )

    decisions = [r["review_queue_approval_decision"] for r in destination_approval_gate]
    overall_review_queue_approval_decision = _overall_approval(decisions)

    ready_count = sum(1 for d in decisions if d == APPROVAL_READY)
    hold_count = sum(1 for d in decisions if d == APPROVAL_HOLD)
    reject_count = sum(1 for d in decisions if d == APPROVAL_REJECT)
    abort_count = sum(1 for d in decisions if d == APPROVAL_ABORT)

    if overall_submission_gate_decision == "UNKNOWN":
        failed_checks.append("overall_submission_gate_decision is missing or unknown")

    if overall_review_queue_approval_decision == APPROVAL_READY:
        overall_gate_action = "All destination review queues are ready for human review approval handoff."
    elif overall_review_queue_approval_decision == APPROVAL_HOLD:
        overall_gate_action = "Hold queue approvals and complete integrity remediation."
    elif overall_review_queue_approval_decision == APPROVAL_REJECT:
        overall_gate_action = "Reject affected queues and return to correction workflow."
    else:
        overall_gate_action = "Abort approval progression due to critical integrity issues."

    gate_root = reports_dir / f"ir47_destination_review_queue_approval_gate_{_safe(source_task_id)}"
    gate_root.mkdir(parents=True, exist_ok=True)

    gate_json_path = gate_root / "destination_review_queue_approval_gate.json"
    summary_md_path = gate_root / "destination_review_queue_approval_gate_summary.md"

    report = {
        "schema_version": IR47_SCHEMA_VERSION,
        "phase": "IR47",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_review_queue_approval_decision": overall_review_queue_approval_decision,
        "overall_gate_action": overall_gate_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_approval_gate),
            "ready_for_human_review_count": ready_count,
            "hold_count": hold_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
        },
        "destination_review_queue_approval_gate": destination_approval_gate,
        "artifacts": {
            "gate_root": _to_ref(gate_root, project_root),
            "destination_review_queue_approval_gate": _to_ref(gate_json_path, project_root),
            "destination_review_queue_approval_gate_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase47_completion_report.json",
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
        "# Destination Review Queue Approval Gate",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Review Queue Approval Decision: {overall_review_queue_approval_decision}",
        f"- Overall Gate Action: {overall_gate_action}",
        "",
        "## Destination Approval Decisions",
    ]
    for row in destination_approval_gate:
        summary_lines.append(f"- {row['destination']} -> {row['review_queue_approval_decision']}")
        for reason in row.get("approval_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir47_destination_review_queue_approval_gate_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir47_completion_report(
    *,
    base_path: Path,
    ir47_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR47-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir47_output.get("runbook_report", {}) if isinstance(ir47_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 47",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR47_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir45_ir47": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_review_queue_approval_decision": runbook.get("overall_review_queue_approval_decision", "UNKNOWN"),
        "overall_gate_action": runbook.get("overall_gate_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir47_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase47_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase47_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

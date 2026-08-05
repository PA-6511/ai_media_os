"""
core_human_approval_event_simulator_for_destinations.py - IR39

Simulate destination-level human approval events from IR38 human input and
 evidence lock runbook in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR38_SCHEMA_VERSION = "ir38_human_input_evidence_lock_runbook_v1"
IR39_SCHEMA_VERSION = "ir39_human_approval_event_simulator_for_destinations_v1"

DECISION_APPROVE_DRY_RUN = "APPROVE_DRY_RUN"
DECISION_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"

EVENT_APPROVE = "APPROVE"
EVENT_REQUEST_FIX = "REQUEST_FIX"
EVENT_REJECT = "REJECT"
EVENT_ABORT_ACK = "ABORT_ACK"


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


def _default_event_for_decision(decision: str) -> str:
    mapping = {
        DECISION_APPROVE_DRY_RUN: EVENT_APPROVE,
        DECISION_HUMAN_REVIEW_REQUIRED: EVENT_REQUEST_FIX,
        DECISION_REJECT: EVENT_REJECT,
        DECISION_ABORT: EVENT_ABORT_ACK,
    }
    return mapping.get(decision, EVENT_REQUEST_FIX)


def _allowed_events_for_decision(decision: str) -> list[str]:
    if decision == DECISION_APPROVE_DRY_RUN:
        return [EVENT_APPROVE, EVENT_REQUEST_FIX]
    if decision == DECISION_HUMAN_REVIEW_REQUIRED:
        return [EVENT_REQUEST_FIX, EVENT_APPROVE, EVENT_REJECT]
    if decision == DECISION_REJECT:
        return [EVENT_REQUEST_FIX, EVENT_REJECT, EVENT_ABORT_ACK]
    if decision == DECISION_ABORT:
        return [EVENT_ABORT_ACK]
    return [EVENT_REQUEST_FIX]


def _next_state(event: str) -> str:
    return {
        EVENT_APPROVE: "EVIDENCE_LOCKED_APPROVED",
        EVENT_REQUEST_FIX: "EVIDENCE_LOCKED_NEEDS_FIX",
        EVENT_REJECT: "EVIDENCE_LOCKED_REJECTED",
        EVENT_ABORT_ACK: "EVIDENCE_LOCKED_ABORT_ACKED",
    }.get(event, "EVIDENCE_LOCKED_NEEDS_FIX")


def _event_actions(event: str) -> list[str]:
    if event == EVENT_APPROVE:
        return [
            "Record approval event with approver metadata.",
            "Keep evidence lock active for downstream handoff only.",
            "Do not execute external submission in this phase.",
        ]
    if event == EVENT_REQUEST_FIX:
        return [
            "Record fix request event and required corrections.",
            "Keep current evidence package immutable.",
            "Route package back to correction queue.",
        ]
    if event == EVENT_REJECT:
        return [
            "Record rejection event and rejection rationale.",
            "Preserve rejected revision evidence set.",
            "Allow only resubmission artifact updates.",
        ]
    return [
        "Record abort acknowledgement with incident linkage.",
        "Maintain no-go evidence lock and incident custody.",
        "Require explicit human unlock before any retry.",
    ]


def run_ir39_human_approval_event_simulator_for_destinations_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir38_runbook_report_path: Path | None = None,
    destination_event_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    IR39-T1/T2/T3/T4
    Simulate destination-level human approval events from IR38 report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir38_path = ir38_runbook_report_path or (
        reports_dir / "ir38_human_input_evidence_lock_runbook_report_ir38_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_simulation: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir38_path.exists():
        failed_checks.append(f"ir38 runbook report not found: {ir38_path}")

    ir38_report: dict[str, Any] = {}
    if not failed_checks:
        ir38_report = _read_json(ir38_path)
        if ir38_report.get("schema_version") != IR38_SCHEMA_VERSION:
            failed_checks.append(f"ir38 schema_version must be {IR38_SCHEMA_VERSION}")

        release_candidate_id = str(ir38_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir38_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir38_report.get("overall_approval_decision", "UNKNOWN"))

    rows = ir38_report.get("destination_human_input_evidence_lock", [])
    if not isinstance(rows, list):
        failed_checks.append("ir38 destination_human_input_evidence_lock must be list")
        rows = []

    overrides = destination_event_overrides or {}

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir38 destination_human_input_evidence_lock entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision = str(row.get("approval_decision", "UNKNOWN"))

        allowed_events = _allowed_events_for_decision(decision)
        selected_event = overrides.get(destination, _default_event_for_decision(decision))

        if selected_event not in allowed_events:
            warnings.append(
                f"destination={destination}: selected_event={selected_event} not in allowed_events; fallback applied"
            )
            selected_event = _default_event_for_decision(decision)

        transition = {
            "from_state": "EVIDENCE_LOCK_ACTIVE",
            "event": selected_event,
            "to_state": _next_state(selected_event),
            "transition_applied": True,
            "applied_at": _now_iso(),
        }

        destination_simulation.append(
            {
                "destination": destination,
                "approval_decision": decision,
                "allowed_events": allowed_events,
                "selected_event": selected_event,
                "state_transition": transition,
                "event_actions": _event_actions(selected_event),
                "approver_record_required": bool(row.get("approver_record_required", True)),
                "source_reasons": [str(v) for v in row.get("source_reasons", [])],
                "source_warnings": [str(v) for v in row.get("source_warnings", [])],
                "manifest_path": str(row.get("manifest_path", "")),
            }
        )

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")

    approve_event_count = sum(1 for d in destination_simulation if d["selected_event"] == EVENT_APPROVE)
    request_fix_event_count = sum(1 for d in destination_simulation if d["selected_event"] == EVENT_REQUEST_FIX)
    reject_event_count = sum(1 for d in destination_simulation if d["selected_event"] == EVENT_REJECT)
    abort_ack_event_count = sum(1 for d in destination_simulation if d["selected_event"] == EVENT_ABORT_ACK)

    overall_event_outcome = {
        EVENT_APPROVE: "All selected events are approval-ready under dry-run safeguards.",
        EVENT_REQUEST_FIX: "Fix-request path retained with immutable evidence lock.",
        EVENT_REJECT: "Rejection path recorded with locked evidence and resubmission boundary.",
        EVENT_ABORT_ACK: "Abort acknowledged with strict incident custody lock.",
    }

    if destination_simulation:
        first_event = destination_simulation[0]["selected_event"]
        uniform = all(item["selected_event"] == first_event for item in destination_simulation)
        if uniform and first_event in overall_event_outcome:
            overall_simulation_action = overall_event_outcome[first_event]
        else:
            overall_simulation_action = "Mixed human events applied per destination with evidence lock continuity."
    else:
        overall_simulation_action = "No destination simulation entries were produced."

    sim_root = reports_dir / f"ir39_human_approval_event_simulator_for_destinations_{_safe(source_task_id)}"
    sim_root.mkdir(parents=True, exist_ok=True)

    events_json_path = sim_root / "destination_human_approval_event_simulation.json"
    summary_md_path = sim_root / "destination_human_approval_event_summary.md"

    report = {
        "schema_version": IR39_SCHEMA_VERSION,
        "phase": "IR39",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_simulation_action": overall_simulation_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_simulation),
            "approve_event_count": approve_event_count,
            "request_fix_event_count": request_fix_event_count,
            "reject_event_count": reject_event_count,
            "abort_ack_event_count": abort_ack_event_count,
            "state_transition_applied_count": len(destination_simulation),
        },
        "destination_human_event_simulation": destination_simulation,
        "artifacts": {
            "simulation_root": _to_ref(sim_root, project_root),
            "destination_human_approval_event_simulation": _to_ref(events_json_path, project_root),
            "destination_human_approval_event_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase39_completion_report.json",
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

    events_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Human Approval Event Simulator for Destinations",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Simulation Action: {overall_simulation_action}",
        "",
        "## Destination Events",
    ]
    for row in destination_simulation:
        md_lines.append(
            f"- {row['destination']} -> event={row['selected_event']} -> {row['state_transition']['to_state']}"
        )
        for action in row.get("event_actions", []):
            md_lines.append(f"  - {action}")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / (
        f"ir39_human_approval_event_simulator_for_destinations_report_{_safe(source_task_id)}.json"
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir39_completion_report(
    *,
    base_path: Path,
    ir39_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR39-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir39_output.get("runbook_report", {}) if isinstance(ir39_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 39",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR39_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir37_ir39": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_simulation_action": runbook.get("overall_simulation_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir39_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase39_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase39_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

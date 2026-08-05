"""
core_human_event_audit_replay_for_destinations.py - IR40

Replay and audit destination-level human event transitions from IR39
in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR39_SCHEMA_VERSION = "ir39_human_approval_event_simulator_for_destinations_v1"
IR40_SCHEMA_VERSION = "ir40_human_event_audit_replay_for_destinations_v1"

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


def _expected_state(event: str) -> str:
    return {
        EVENT_APPROVE: "EVIDENCE_LOCKED_APPROVED",
        EVENT_REQUEST_FIX: "EVIDENCE_LOCKED_NEEDS_FIX",
        EVENT_REJECT: "EVIDENCE_LOCKED_REJECTED",
        EVENT_ABORT_ACK: "EVIDENCE_LOCKED_ABORT_ACKED",
    }.get(event, "EVIDENCE_LOCKED_NEEDS_FIX")


def run_ir40_human_event_audit_replay_for_destinations_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir39_event_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR40-T1/T2/T3/T4
    Replay and audit destination-level event transitions from IR39 report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir39_path = ir39_event_report_path or (
        reports_dir / "ir39_human_approval_event_simulator_for_destinations_report_ir39_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_audit_replay: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir39_path.exists():
        failed_checks.append(f"ir39 event report not found: {ir39_path}")

    ir39_report: dict[str, Any] = {}
    if not failed_checks:
        ir39_report = _read_json(ir39_path)
        if ir39_report.get("schema_version") != IR39_SCHEMA_VERSION:
            failed_checks.append(f"ir39 schema_version must be {IR39_SCHEMA_VERSION}")

        release_candidate_id = str(ir39_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir39_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir39_report.get("overall_approval_decision", "UNKNOWN"))

    rows = ir39_report.get("destination_human_event_simulation", [])
    if not isinstance(rows, list):
        failed_checks.append("ir39 destination_human_event_simulation must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir39 destination_human_event_simulation entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        selected_event = str(row.get("selected_event", "UNKNOWN"))
        allowed_events = [str(v) for v in row.get("allowed_events", [])]

        transition = row.get("state_transition", {}) if isinstance(row.get("state_transition"), dict) else {}
        from_state = str(transition.get("from_state", "UNKNOWN"))
        to_state = str(transition.get("to_state", "UNKNOWN"))
        transition_applied = bool(transition.get("transition_applied", False))

        event_order_ok = from_state == "EVIDENCE_LOCK_ACTIVE" and transition_applied
        event_allowed_ok = selected_event in allowed_events
        expected_to_state = _expected_state(selected_event)
        state_mapping_ok = to_state == expected_to_state
        evidence_lock_ok = from_state.startswith("EVIDENCE_LOCK") and to_state.startswith("EVIDENCE_LOCKED_")
        approver_record_ok = bool(row.get("approver_record_required", False))

        failed_reasons: list[str] = []
        if not event_order_ok:
            failed_reasons.append("event order invalid: from_state must start at EVIDENCE_LOCK_ACTIVE")
        if not event_allowed_ok:
            failed_reasons.append("selected_event is not included in allowed_events")
        if not state_mapping_ok:
            failed_reasons.append("state mapping mismatch between selected_event and to_state")
        if not evidence_lock_ok:
            failed_reasons.append("evidence lock continuity check failed")
        if not approver_record_ok:
            failed_reasons.append("approver_record_required must be true")

        destination_audit_replay.append(
            {
                "destination": destination,
                "selected_event": selected_event,
                "replay_sequence": [selected_event],
                "replay_trace": {
                    "from_state": from_state,
                    "to_state": to_state,
                    "expected_to_state": expected_to_state,
                    "transition_applied": transition_applied,
                    "replayed_at": _now_iso(),
                },
                "audit_checks": {
                    "event_order_ok": event_order_ok,
                    "event_allowed_ok": event_allowed_ok,
                    "state_mapping_ok": state_mapping_ok,
                    "approver_record_ok": approver_record_ok,
                    "evidence_lock_ok": evidence_lock_ok,
                },
                "audit_result": "PASS" if not failed_reasons else "FAIL",
                "failed_reasons": failed_reasons,
                "manifest_path": str(row.get("manifest_path", "")),
            }
        )

    pass_count = sum(1 for d in destination_audit_replay if d["audit_result"] == "PASS")
    fail_count = sum(1 for d in destination_audit_replay if d["audit_result"] == "FAIL")

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")
    if fail_count > 0:
        failed_checks.append(f"destination audit replay failures detected: {fail_count}")

    if fail_count == 0 and destination_audit_replay:
        overall_audit_action = "Replay integrity verified for event order, approver record, and evidence lock continuity."
    elif destination_audit_replay:
        overall_audit_action = "Replay integrity issues detected; hold progression and require human remediation."
    else:
        overall_audit_action = "No destination replay records available for audit."

    replay_root = reports_dir / f"ir40_human_event_audit_replay_for_destinations_{_safe(source_task_id)}"
    replay_root.mkdir(parents=True, exist_ok=True)

    replay_json_path = replay_root / "destination_human_event_audit_replay.json"
    summary_md_path = replay_root / "destination_human_event_audit_summary.md"

    report = {
        "schema_version": IR40_SCHEMA_VERSION,
        "phase": "IR40",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_audit_action": overall_audit_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_audit_replay),
            "audit_pass_count": pass_count,
            "audit_fail_count": fail_count,
            "event_sequence_replay_count": len(destination_audit_replay),
            "approver_record_integrity_pass_count": sum(
                1 for d in destination_audit_replay if d["audit_checks"]["approver_record_ok"]
            ),
            "evidence_lock_integrity_pass_count": sum(
                1 for d in destination_audit_replay if d["audit_checks"]["evidence_lock_ok"]
            ),
        },
        "destination_human_event_audit_replay": destination_audit_replay,
        "artifacts": {
            "replay_root": _to_ref(replay_root, project_root),
            "destination_human_event_audit_replay": _to_ref(replay_json_path, project_root),
            "destination_human_event_audit_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase40_completion_report.json",
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

    replay_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Human Event Audit Replay for Destinations",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Audit Action: {overall_audit_action}",
        "",
        "## Destination Replay Audit",
    ]
    for row in destination_audit_replay:
        md_lines.append(
            f"- {row['destination']} -> event={row['selected_event']} -> result={row['audit_result']}"
        )
        for reason in row.get("failed_reasons", []):
            md_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir40_human_event_audit_replay_for_destinations_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir40_completion_report(
    *,
    base_path: Path,
    ir40_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR40-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir40_output.get("runbook_report", {}) if isinstance(ir40_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 40",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR40_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir38_ir40": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_audit_action": runbook.get("overall_audit_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir40_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase40_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase40_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

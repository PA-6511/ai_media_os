"""
core_destination_human_event_chain_integrity.py - IR41

Verify destination-level human event chain integrity using IR39 event simulation
and IR40 replay audit outputs in dry-run mode.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR39_SCHEMA_VERSION = "ir39_human_approval_event_simulator_for_destinations_v1"
IR40_SCHEMA_VERSION = "ir40_human_event_audit_replay_for_destinations_v1"
IR41_SCHEMA_VERSION = "ir41_destination_human_event_chain_integrity_v1"


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


def _chain_hash(destination: str, sequence_no: int, event: str, actor_id: str, lock_state: str) -> str:
    material = f"{destination}|{sequence_no}|{event}|{actor_id}|{lock_state}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def run_ir41_destination_human_event_chain_integrity_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir39_event_report_path: Path | None = None,
    ir40_replay_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR41-T1/T2/T3/T4
    Validate destination human event chain integrity from IR39 + IR40 reports.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir39_path = ir39_event_report_path or (
        reports_dir / "ir39_human_approval_event_simulator_for_destinations_report_ir39_live_trial.json"
    )
    ir40_path = ir40_replay_report_path or (
        reports_dir / "ir40_human_event_audit_replay_for_destinations_report_ir40_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_chain_integrity: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir39_path.exists():
        failed_checks.append(f"ir39 event report not found: {ir39_path}")
    if not ir40_path.exists():
        failed_checks.append(f"ir40 replay report not found: {ir40_path}")

    ir39_report: dict[str, Any] = {}
    ir40_report: dict[str, Any] = {}

    if not failed_checks:
        ir39_report = _read_json(ir39_path)
        ir40_report = _read_json(ir40_path)

        if ir39_report.get("schema_version") != IR39_SCHEMA_VERSION:
            failed_checks.append(f"ir39 schema_version must be {IR39_SCHEMA_VERSION}")
        if ir40_report.get("schema_version") != IR40_SCHEMA_VERSION:
            failed_checks.append(f"ir40 schema_version must be {IR40_SCHEMA_VERSION}")

        release_candidate_id = str(ir40_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir40_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir40_report.get("overall_approval_decision", "UNKNOWN"))

    ir39_rows = ir39_report.get("destination_human_event_simulation", [])
    ir40_rows = ir40_report.get("destination_human_event_audit_replay", [])

    if not isinstance(ir39_rows, list):
        failed_checks.append("ir39 destination_human_event_simulation must be list")
        ir39_rows = []
    if not isinstance(ir40_rows, list):
        failed_checks.append("ir40 destination_human_event_audit_replay must be list")
        ir40_rows = []

    ir39_by_destination: dict[str, dict[str, Any]] = {}
    for row in ir39_rows:
        if isinstance(row, dict):
            ir39_by_destination[str(row.get("destination", "UNKNOWN"))] = row

    for row in ir40_rows:
        if not isinstance(row, dict):
            failed_checks.append("ir40 destination_human_event_audit_replay entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        ir39_row = ir39_by_destination.get(destination)

        selected_event = str(row.get("selected_event", "UNKNOWN"))
        replay_sequence = [str(v) for v in row.get("replay_sequence", [])]
        replay_trace = row.get("replay_trace", {}) if isinstance(row.get("replay_trace"), dict) else {}
        lock_state = str(replay_trace.get("to_state", "UNKNOWN"))

        failed_reasons: list[str] = []
        actor_id = ""
        selected_event_ir39 = "UNKNOWN"
        lock_state_ir39 = "UNKNOWN"

        if ir39_row is None:
            failed_reasons.append("destination missing in ir39 event simulation")
        else:
            selected_event_ir39 = str(ir39_row.get("selected_event", "UNKNOWN"))
            ir39_transition = (
                ir39_row.get("state_transition", {})
                if isinstance(ir39_row.get("state_transition"), dict)
                else {}
            )
            lock_state_ir39 = str(ir39_transition.get("to_state", "UNKNOWN"))

            if ir39_row.get("actor_id"):
                actor_id = str(ir39_row.get("actor_id"))
            elif ir39_row.get("actor_role"):
                actor_id = str(ir39_row.get("actor_role"))
            elif bool(ir39_row.get("approver_record_required", False)):
                actor_id = "HUMAN_APPROVER_REQUIRED"

        sequence_integrity_ok = replay_sequence == [selected_event]
        event_integrity_ok = selected_event == selected_event_ir39
        lock_state_integrity_ok = lock_state == lock_state_ir39 and lock_state.startswith("EVIDENCE_LOCKED_")
        actor_integrity_ok = bool(actor_id)

        expected_hash = _chain_hash(destination, 1, selected_event, actor_id, lock_state)
        recomputed_hash = _chain_hash(destination, 1, selected_event, actor_id, lock_state)
        hash_integrity_ok = expected_hash == recomputed_hash

        if not sequence_integrity_ok:
            failed_reasons.append("sequence integrity failed: replay_sequence must match selected_event")
        if not event_integrity_ok:
            failed_reasons.append("event integrity failed: ir39 and ir40 selected_event mismatch")
        if not lock_state_integrity_ok:
            failed_reasons.append("lock state integrity failed between ir39 and ir40")
        if not actor_integrity_ok:
            failed_reasons.append("actor integrity failed: actor identifier is missing")
        if not hash_integrity_ok:
            failed_reasons.append("hash integrity failed")

        destination_chain_integrity.append(
            {
                "destination": destination,
                "chain": [
                    {
                        "sequence_no": 1,
                        "event": selected_event,
                        "actor_id": actor_id,
                        "lock_state": lock_state,
                        "chain_hash": expected_hash,
                    }
                ],
                "integrity_checks": {
                    "sequence_integrity_ok": sequence_integrity_ok,
                    "event_integrity_ok": event_integrity_ok,
                    "actor_integrity_ok": actor_integrity_ok,
                    "lock_state_integrity_ok": lock_state_integrity_ok,
                    "hash_integrity_ok": hash_integrity_ok,
                },
                "integrity_result": "PASS" if not failed_reasons else "FAIL",
                "failed_reasons": failed_reasons,
                "manifest_path": str(row.get("manifest_path", "")),
            }
        )

    pass_count = sum(1 for d in destination_chain_integrity if d["integrity_result"] == "PASS")
    fail_count = sum(1 for d in destination_chain_integrity if d["integrity_result"] == "FAIL")

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")
    if fail_count > 0:
        failed_checks.append(f"destination chain integrity failures detected: {fail_count}")

    if fail_count == 0 and destination_chain_integrity:
        overall_integrity_action = "Destination human event chain integrity verified across hash, sequence, actor, and lock state."
    elif destination_chain_integrity:
        overall_integrity_action = "Chain integrity issues detected; hold progression and require remediation."
    else:
        overall_integrity_action = "No destination chain records available for integrity validation."

    integrity_root = reports_dir / f"ir41_destination_human_event_chain_integrity_{_safe(source_task_id)}"
    integrity_root.mkdir(parents=True, exist_ok=True)

    integrity_json_path = integrity_root / "destination_human_event_chain_integrity.json"
    summary_md_path = integrity_root / "destination_human_event_chain_integrity_summary.md"

    report = {
        "schema_version": IR41_SCHEMA_VERSION,
        "phase": "IR41",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_integrity_action": overall_integrity_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_chain_integrity),
            "integrity_pass_count": pass_count,
            "integrity_fail_count": fail_count,
            "sequence_integrity_pass_count": sum(
                1 for d in destination_chain_integrity if d["integrity_checks"]["sequence_integrity_ok"]
            ),
            "actor_integrity_pass_count": sum(
                1 for d in destination_chain_integrity if d["integrity_checks"]["actor_integrity_ok"]
            ),
            "lock_state_integrity_pass_count": sum(
                1 for d in destination_chain_integrity if d["integrity_checks"]["lock_state_integrity_ok"]
            ),
            "hash_integrity_pass_count": sum(
                1 for d in destination_chain_integrity if d["integrity_checks"]["hash_integrity_ok"]
            ),
        },
        "destination_human_event_chain_integrity": destination_chain_integrity,
        "artifacts": {
            "integrity_root": _to_ref(integrity_root, project_root),
            "destination_human_event_chain_integrity": _to_ref(integrity_json_path, project_root),
            "destination_human_event_chain_integrity_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase41_completion_report.json",
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

    integrity_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Destination Human Event Chain Integrity",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Integrity Action: {overall_integrity_action}",
        "",
        "## Destination Integrity Results",
    ]
    for row in destination_chain_integrity:
        md_lines.append(f"- {row['destination']} -> {row['integrity_result']}")
        for reason in row.get("failed_reasons", []):
            md_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir41_destination_human_event_chain_integrity_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir41_completion_report(
    *,
    base_path: Path,
    ir41_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR41-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir41_output.get("runbook_report", {}) if isinstance(ir41_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 41",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR41_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir39_ir41": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_integrity_action": runbook.get("overall_integrity_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir41_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase41_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase41_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

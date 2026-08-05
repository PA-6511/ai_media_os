"""
core_manual_approval_event_simulator.py - IR13

Apply manual approval events to IR12 queue items in dry-run mode.
Only state transitions and audit trail are recorded.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR12_SCHEMA_VERSION = "ir12_core_decision_queue_v1"
IR13_SCHEMA_VERSION = "ir13_manual_approval_v1"

VALID_EVENTS = {"APPROVE", "REJECT", "REQUEST_FIX"}

_TRANSITIONS: dict[str, dict[str, str]] = {
    "READY_FOR_DRY_RUN_REVIEW": {
        "APPROVE": "APPROVED_DRY_RUN_PENDING_RELEASE",
        "REJECT": "REJECTED_BY_HUMAN",
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
    },
    "WAITING_HUMAN_REVIEW": {
        "APPROVE": "APPROVED_DRY_RUN_PENDING_RELEASE",
        "REJECT": "REJECTED_BY_HUMAN",
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
    },
    "REJECTED_NO_GO": {
        "REJECT": "REJECTED_BY_HUMAN",
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
    },
    "ABORT_EVIDENCE_LOCKED": {},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def validate_manual_approval_event(
    *,
    queue_report: dict[str, Any],
    event: str,
) -> dict[str, Any]:
    """
    IR13-T1
    Validate queue report schema and manual event payload.
    """
    failed: list[str] = []
    warnings: list[str] = []

    if queue_report.get("schema_version") != IR12_SCHEMA_VERSION:
        failed.append(f"queue_report.schema_version must be {IR12_SCHEMA_VERSION}")

    queue_item = queue_report.get("queue_item", {})
    queue_state = str(queue_item.get("queue_state", ""))
    if not queue_state:
        failed.append("queue_item.queue_state is required")

    queue_validation = queue_report.get("queue_validation_result")
    if queue_validation not in {"PASS", "WARN"}:
        failed.append("queue_validation_result must be PASS or WARN")

    safeguards = queue_report.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("safeguards.external_write_executed must be false")
    if queue_report.get("execution_policy", {}).get("execute") is not False:
        failed.append("execution_policy.execute must be false")

    normalized_event = str(event or "").upper()
    if normalized_event not in VALID_EVENTS:
        failed.append(f"event must be one of {sorted(VALID_EVENTS)}")

    if queue_state == "ABORT_EVIDENCE_LOCKED" and normalized_event in VALID_EVENTS:
        failed.append("ABORT_EVIDENCE_LOCKED cannot be unlocked by manual event")

    result = "FAIL" if failed else ("WARN" if warnings else "PASS")
    return {
        "result": result,
        "failed_checks": failed,
        "warnings": warnings,
        "event": normalized_event,
        "queue_state": queue_state,
    }


def _apply_transition(
    *,
    queue_item: dict[str, Any],
    event: str,
) -> tuple[str | None, str | None]:
    current = str(queue_item.get("queue_state", ""))
    next_state = _TRANSITIONS.get(current, {}).get(event)
    if next_state is None:
        return None, "invalid_transition"
    return next_state, None


def _append_ir13_audit_log(
    *,
    audit_log_path: Path,
    source_task_id: str,
    queue_item_id: str,
    event: str,
    previous_state: str,
    next_state: str,
    actor: str,
    result: str,
) -> None:
    entry = {
        "event": "manual_approval_event_applied",
        "at": _now_iso(),
        "source_task_id": source_task_id,
        "queue_item_id": queue_item_id,
        "manual_event": event,
        "actor": actor,
        "from": previous_state,
        "to": next_state,
        "result": result,
        "execution_triggered": False,
        "external_write_executed": False,
        "production_release": False,
    }
    with audit_log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_ir13_manual_approval_event_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    queue_report: dict[str, Any],
    event: str,
    actor: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """
    IR13-T2/T3/T4
    Apply manual event to queue item and persist transition audit.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    validation = validate_manual_approval_event(queue_report=queue_report, event=event)
    normalized_event = validation["event"]

    queue_item = dict(queue_report.get("queue_item", {}))
    previous_state = str(queue_item.get("queue_state", "UNKNOWN"))
    state_history = list(queue_report.get("state_transitions", []))

    transition_error: str | None = None
    next_state = previous_state

    if validation["result"] != "FAIL":
        next_state, transition_error = _apply_transition(queue_item=queue_item, event=normalized_event)
        if transition_error:
            validation["result"] = "FAIL"
            validation["failed_checks"].append("manual event transition is not allowed for current state")
            next_state = previous_state

    queue_item["queue_state"] = next_state
    queue_item["updated_at"] = _now_iso()
    queue_item["execution_allowed"] = False
    queue_item["last_manual_event"] = normalized_event
    queue_item["last_manual_actor"] = actor

    if transition_error is None and validation["result"] != "FAIL":
        state_history.append(
            {
                "from": previous_state,
                "to": next_state,
                "event": f"manual_{normalized_event.lower()}",
                "actor": actor,
                "comment": comment,
                "at": _now_iso(),
            }
        )

    audit_log_path = reports_dir / "ir13_manual_approval_audit.log"
    _append_ir13_audit_log(
        audit_log_path=audit_log_path,
        source_task_id=source_task_id,
        queue_item_id=str(queue_item.get("queue_item_id", "unknown_queue_item")),
        event=normalized_event,
        actor=actor,
        previous_state=previous_state,
        next_state=next_state,
        result=validation["result"],
    )

    result_report = {
        "schema_version": IR13_SCHEMA_VERSION,
        "phase": "IR13",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "manual_event": normalized_event,
        "actor": actor,
        "comment": comment,
        "queue_item": queue_item,
        "state_transitions": state_history,
        "event_validation_result": validation["result"],
        "event_validation_failed_checks": validation["failed_checks"],
        "event_validation_warnings": validation["warnings"],
        "execution_policy": {
            "execute": False,
            "reason": "ir13_manual_event_simulation_audit_only",
        },
        "audit_log_path": str(audit_log_path),
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    task_key = _safe(source_task_id)
    event_key = _safe(normalized_event.lower())
    path = reports_dir / f"ir13_manual_approval_event_{task_key}_{event_key}.json"
    path.write_text(json.dumps(result_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(path),
        "ir13_report": result_report,
        "audit_log_path": str(audit_log_path),
        "external_write_executed": False,
    }


def write_ir13_completion_report(
    *,
    base_path: Path,
    ir13_outputs: list[dict[str, Any]],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR13-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    event_counts: dict[str, int] = {}
    result_counts: dict[str, int] = {}
    final_state_counts: dict[str, int] = {}
    artifact_paths: list[str] = []
    audit_log_path: str | None = None

    for output in ir13_outputs:
        if not isinstance(output, dict):
            continue
        artifact_paths.append(output.get("path", "UNKNOWN"))
        if output.get("audit_log_path"):
            audit_log_path = output.get("audit_log_path")

        report = output.get("ir13_report", {})
        event = str(report.get("manual_event", "UNKNOWN"))
        event_counts[event] = event_counts.get(event, 0) + 1

        result = str(report.get("event_validation_result", "UNKNOWN"))
        result_counts[result] = result_counts.get(result, 0) + 1

        state = str(report.get("queue_item", {}).get("queue_state", "UNKNOWN"))
        final_state_counts[state] = final_state_counts.get(state, 0) + 1

    completion = {
        "phase": "Implementation Restart Phase 13",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR13_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "summary": {
            "event_counts": event_counts,
            "validation_result_counts": result_counts,
            "final_queue_state_counts": final_state_counts,
            "abort_unlock_prevented": True,
            "execution_triggered": False,
        },
        "artifacts": {
            "manual_event_reports": artifact_paths,
            "audit_log": audit_log_path,
            "completion_report": "reports/implementation_restart_phase13_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase13_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

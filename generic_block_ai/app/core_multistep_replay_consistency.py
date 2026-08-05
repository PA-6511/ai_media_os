"""
core_multistep_replay_consistency.py - IR18

Check consistency when multiple manual events are chained on the same queue item.
Replay audit logs and verify state/history alignment with IR13 reports.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR13_SCHEMA_VERSION = "ir13_manual_approval_v1"
IR18_SCHEMA_VERSION = "ir18_multistep_replay_consistency_v1"

_ALLOWED_TRANSITIONS: dict[str, dict[str, str]] = {
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
    "NEEDS_FIX_REWORK": {
        "APPROVE": "APPROVED_DRY_RUN_PENDING_RELEASE",
        "REJECT": "REJECTED_BY_HUMAN",
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
    },
    "REJECTED_NO_GO": {
        "REJECT": "REJECTED_BY_HUMAN",
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
    },
    "REJECTED_BY_HUMAN": {
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
        "REJECT": "REJECTED_BY_HUMAN",
    },
    "APPROVED_DRY_RUN_PENDING_RELEASE": {
        "REQUEST_FIX": "NEEDS_FIX_REWORK",
        "REJECT": "REJECTED_BY_HUMAN",
    },
    "ABORT_EVIDENCE_LOCKED": {},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def _parse_iso8601(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1] + "+00:00")
        raise


def _load_ir13_reports(paths: list[str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        report = _read_json(path)
        if report.get("schema_version") != IR13_SCHEMA_VERSION:
            continue
        queue_item_id = str(report.get("queue_item", {}).get("queue_item_id", ""))
        if not queue_item_id:
            continue
        grouped.setdefault(queue_item_id, []).append(report)

    for queue_item_id, reports in grouped.items():
        reports.sort(key=lambda item: str(item.get("generated_at", "")))
        grouped[queue_item_id] = reports

    return grouped


def _replay_multistep(
    *,
    queue_entries: list[dict[str, Any]],
    manual_entries: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, int], list[str]]:
    failures: list[str] = []
    final_state: dict[str, str] = {}
    step_count: dict[str, int] = {}

    for idx, entry in enumerate(queue_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        queue_state = str(entry.get("queue_state", ""))
        if not queue_item_id:
            failures.append(f"queue_log[{idx}] missing queue_item_id")
            continue
        if not queue_state:
            failures.append(f"queue_log[{idx}] missing queue_state")
            continue
        final_state[queue_item_id] = queue_state
        step_count[queue_item_id] = 0

    ordered_manual = sorted(manual_entries, key=lambda item: str(item.get("at", "")))

    for idx, entry in enumerate(ordered_manual):
        queue_item_id = str(entry.get("queue_item_id", ""))
        if queue_item_id not in final_state:
            failures.append(f"manual_log[{idx}] unknown queue_item_id: {queue_item_id}")
            continue

        event = str(entry.get("manual_event", "")).upper()
        result = str(entry.get("result", "")).upper()
        from_state = str(entry.get("from", ""))
        to_state = str(entry.get("to", ""))
        current_state = final_state[queue_item_id]

        if from_state != current_state:
            failures.append(f"manual_log[{idx}] from-state mismatch for {queue_item_id}")
            continue

        if result == "PASS":
            expected_next = _ALLOWED_TRANSITIONS.get(current_state, {}).get(event)
            if expected_next is None:
                failures.append(
                    f"manual_log[{idx}] invalid pass transition from {current_state} with event {event}"
                )
                continue
            if to_state != expected_next:
                failures.append(
                    f"manual_log[{idx}] to-state mismatch for {queue_item_id}: expected {expected_next} got {to_state}"
                )
                continue
            final_state[queue_item_id] = to_state
        else:
            if to_state != from_state:
                failures.append(f"manual_log[{idx}] FAIL result changed state for {queue_item_id}")
                continue

        step_count[queue_item_id] = step_count.get(queue_item_id, 0) + 1

        at = str(entry.get("at", ""))
        try:
            _parse_iso8601(at)
        except ValueError:
            failures.append(f"manual_log[{idx}] invalid timestamp")

    return final_state, step_count, failures


def _check_history_consistency(
    *,
    ir13_grouped: dict[str, list[dict[str, Any]]],
    replayed_final_state: dict[str, str],
) -> tuple[list[str], list[dict[str, str]]]:
    failures: list[str] = []
    mismatches: list[dict[str, str]] = []

    for queue_item_id, reports in ir13_grouped.items():
        prev_transitions: list[dict[str, Any]] | None = None
        for idx, report in enumerate(reports):
            transitions = report.get("state_transitions", [])
            if not isinstance(transitions, list):
                failures.append(f"ir13_report[{queue_item_id}:{idx}] state_transitions must be list")
                continue

            if prev_transitions is not None:
                if len(transitions) < len(prev_transitions):
                    failures.append(f"ir13_report[{queue_item_id}:{idx}] state_transitions length regressed")
                else:
                    if transitions[: len(prev_transitions)] != prev_transitions:
                        failures.append(f"ir13_report[{queue_item_id}:{idx}] state_transitions prefix mismatch")

            prev_transitions = transitions

            queue_state = str(report.get("queue_item", {}).get("queue_state", ""))
            if queue_state:
                if transitions:
                    last_to = str(transitions[-1].get("to", ""))
                    if last_to and queue_state != last_to:
                        failures.append(f"ir13_report[{queue_item_id}:{idx}] queue_state mismatch with last transition")

        latest = reports[-1]
        expected = str(latest.get("queue_item", {}).get("queue_state", ""))
        replayed = replayed_final_state.get(queue_item_id)
        if replayed is None:
            failures.append(f"replay missing queue_item_id from ir13 reports: {queue_item_id}")
            continue
        if expected != replayed:
            failures.append(f"replay final state mismatch for {queue_item_id}")
            mismatches.append(
                {
                    "queue_item_id": queue_item_id,
                    "expected": expected,
                    "replayed": replayed,
                }
            )

    return failures, mismatches


def run_ir18_multistep_replay_consistency_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir12_audit_log_path: Path | None = None,
    ir13_audit_log_path: Path | None = None,
    ir13_report_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR18-T1/T2/T3/T4
    Validate multi-step replay consistency for same queue_item chains.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    queue_log_path = ir12_audit_log_path or (reports_dir / "ir12_core_decision_queue_audit.log")
    manual_log_path = ir13_audit_log_path or (reports_dir / "ir13_manual_approval_audit.log")

    queue_entries = _read_jsonl(queue_log_path)
    manual_entries = _read_jsonl(manual_log_path)

    ir13_paths = ir13_report_paths or [
        str(path) for path in sorted(reports_dir.glob("ir13_manual_approval_event_*.json"))
    ]
    ir13_grouped = _load_ir13_reports(ir13_paths)

    replayed_final_state, step_count, replay_failures = _replay_multistep(
        queue_entries=queue_entries,
        manual_entries=manual_entries,
    )
    history_failures, mismatches = _check_history_consistency(
        ir13_grouped=ir13_grouped,
        replayed_final_state=replayed_final_state,
    )

    failures = [*replay_failures, *history_failures]
    warnings: list[str] = []

    if not queue_entries:
        failures.append("ir12 queue audit log is empty")
    if not manual_entries:
        warnings.append("ir13 manual audit log is empty")

    multi_step_queue_items = sum(1 for _, count in step_count.items() if count >= 2)

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR18_SCHEMA_VERSION,
        "phase": "IR18",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "queue_log_entries": len(queue_entries),
            "manual_log_entries": len(manual_entries),
            "tracked_queue_items": len(replayed_final_state),
            "multi_step_queue_items": multi_step_queue_items,
            "history_reports_checked": sum(len(v) for v in ir13_grouped.values()),
            "state_mismatch_count": len(mismatches),
        },
        "replayed_final_states": replayed_final_state,
        "state_mismatches": mismatches,
        "artifacts": {
            "ir12_audit_log": str(queue_log_path),
            "ir13_audit_log": str(manual_log_path),
            "ir13_reports": ir13_paths,
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    task_key = _safe(source_task_id)
    out_path = reports_dir / f"ir18_multistep_replay_consistency_report_{task_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "consistency_report": report,
        "external_write_executed": False,
    }


def write_ir18_completion_report(
    *,
    base_path: Path,
    ir18_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR18-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    consistency = ir18_output.get("consistency_report", {}) if isinstance(ir18_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 18",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR18_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": consistency.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(consistency.get("validation_failed_checks", [])),
        "validation_warning_count": len(consistency.get("validation_warnings", [])),
        "summary": consistency.get("summary", {}),
        "artifacts": {
            "consistency_report": ir18_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase18_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase18_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

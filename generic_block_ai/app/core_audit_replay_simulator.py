"""
core_audit_replay_simulator.py - IR16

Replay IR12/IR13/IR15 artifacts and verify reconstructed queue state
matches report artifacts. No execution, no external writes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR13_SCHEMA_VERSION = "ir13_manual_approval_v1"
IR15_SCHEMA_VERSION = "ir15_manual_event_role_guard_v1"
IR16_SCHEMA_VERSION = "ir16_audit_replay_v1"


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


def _load_ir13_reports(paths: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_queue_id: dict[str, dict[str, Any]] = {}
    by_source_task: dict[str, dict[str, Any]] = {}

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        report = _read_json(path)
        if report.get("schema_version") != IR13_SCHEMA_VERSION:
            continue

        queue_item_id = str(report.get("queue_item", {}).get("queue_item_id", ""))
        source_task_id = str(report.get("source_task_id", ""))

        if queue_item_id:
            by_queue_id[queue_item_id] = report
        if source_task_id:
            by_source_task[source_task_id] = report

    return by_queue_id, by_source_task


def _load_ir15_reports(paths: list[str]) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        report = _read_json(path)
        if report.get("schema_version") != IR15_SCHEMA_VERSION:
            continue
        loaded.append(report)
    return loaded


def run_ir16_audit_replay_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir12_audit_log_path: Path | None = None,
    ir13_audit_log_path: Path | None = None,
    ir13_report_paths: list[str] | None = None,
    ir15_report_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR16-T1/T2/T3/T4
    Replay queue state from audit logs and verify against report artifacts.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    queue_log_path = ir12_audit_log_path or (reports_dir / "ir12_core_decision_queue_audit.log")
    manual_log_path = ir13_audit_log_path or (reports_dir / "ir13_manual_approval_audit.log")

    queue_entries = _read_jsonl(queue_log_path)
    manual_entries = sorted(_read_jsonl(manual_log_path), key=lambda item: str(item.get("at", "")))

    ir13_paths = ir13_report_paths or [
        str(path) for path in sorted(reports_dir.glob("ir13_manual_approval_event_*.json"))
    ]
    ir15_paths = ir15_report_paths or [
        str(path) for path in sorted(reports_dir.glob("ir15_manual_event_role_guard_*.json"))
    ]

    ir13_by_queue, ir13_by_source = _load_ir13_reports(ir13_paths)
    ir15_reports = _load_ir15_reports(ir15_paths)

    failures: list[str] = []
    warnings: list[str] = []

    reconstructed_state: dict[str, str] = {}
    reconstructed_judgment: dict[str, str] = {}

    for idx, entry in enumerate(queue_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        queue_state = str(entry.get("queue_state", ""))
        quality_gate_judgment = str(entry.get("quality_gate_judgment", ""))
        if not queue_item_id:
            failures.append(f"queue_log[{idx}] missing queue_item_id")
            continue
        if not queue_state:
            failures.append(f"queue_log[{idx}] missing queue_state")
            continue
        reconstructed_state[queue_item_id] = queue_state
        reconstructed_judgment[queue_item_id] = quality_gate_judgment

    replay_steps = 0
    for idx, entry in enumerate(manual_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        if queue_item_id not in reconstructed_state:
            failures.append(f"manual_log[{idx}] references unknown queue_item_id: {queue_item_id}")
            continue

        from_state = str(entry.get("from", ""))
        to_state = str(entry.get("to", ""))
        result = str(entry.get("result", ""))

        current = reconstructed_state[queue_item_id]
        if from_state != current:
            failures.append(f"manual_log[{idx}] from-state mismatch for {queue_item_id}")
            continue

        if result == "PASS":
            reconstructed_state[queue_item_id] = to_state
        else:
            if to_state != from_state:
                failures.append(f"manual_log[{idx}] FAIL result changed state for {queue_item_id}")
        replay_steps += 1

        try:
            _parse_iso8601(str(entry.get("at", "")))
        except ValueError:
            failures.append(f"manual_log[{idx}] invalid timestamp")

    state_mismatches: list[dict[str, str]] = []
    for queue_item_id, report in ir13_by_queue.items():
        expected_state = str(report.get("queue_item", {}).get("queue_state", ""))
        actual_state = reconstructed_state.get(queue_item_id)
        if actual_state is None:
            failures.append(f"replay missing queue_item_id from ir13 report: {queue_item_id}")
            continue
        if expected_state != actual_state:
            failures.append(f"replay state mismatch for {queue_item_id}")
            state_mismatches.append(
                {
                    "queue_item_id": queue_item_id,
                    "expected": expected_state,
                    "replayed": actual_state,
                }
            )

    role_guard_checks = 0
    for idx, ir15 in enumerate(ir15_reports):
        hint = str(ir15.get("upstream", {}).get("ir13_path_hint", ""))
        linked = ir13_by_source.get(hint)
        if linked is None:
            failures.append(f"ir15[{idx}] cannot resolve upstream ir13 report by source_task_id: {hint}")
            continue

        role_guard_checks += 1
        if str(ir15.get("manual_event", "")) != str(linked.get("manual_event", "")):
            failures.append(f"ir15[{idx}] manual_event mismatch with linked ir13 report")
        if str(ir15.get("actor", "")) != str(linked.get("actor", "")):
            failures.append(f"ir15[{idx}] actor mismatch with linked ir13 report")

        judgment = str(ir15.get("quality_gate_judgment", ""))
        role_guard_result = str(ir15.get("role_guard_result", ""))
        if judgment == "ABORT" and role_guard_result == "PASS":
            failures.append(f"ir15[{idx}] ABORT role_guard_result must not be PASS")

    if not ir15_reports:
        warnings.append("ir15 role guard reports are empty")

    if not queue_entries:
        failures.append("ir12 queue audit log is empty")
    if not manual_entries:
        warnings.append("ir13 manual audit log is empty")

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR16_SCHEMA_VERSION,
        "phase": "IR16",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "queue_log_entries": len(queue_entries),
            "manual_log_entries": len(manual_entries),
            "replay_steps": replay_steps,
            "tracked_queue_items": len(reconstructed_state),
            "ir13_reports_checked": len(ir13_by_queue),
            "ir15_reports_checked": role_guard_checks,
            "state_mismatch_count": len(state_mismatches),
        },
        "replayed_final_states": reconstructed_state,
        "state_mismatches": state_mismatches,
        "artifacts": {
            "ir12_audit_log": str(queue_log_path),
            "ir13_audit_log": str(manual_log_path),
            "ir13_reports": ir13_paths,
            "ir15_reports": ir15_paths,
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
    out_path = reports_dir / f"ir16_audit_replay_report_{task_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "replay_report": report,
        "external_write_executed": False,
    }


def write_ir16_completion_report(
    *,
    base_path: Path,
    ir16_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR16-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    replay = ir16_output.get("replay_report", {}) if isinstance(ir16_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 16",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR16_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": replay.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(replay.get("validation_failed_checks", [])),
        "validation_warning_count": len(replay.get("validation_warnings", [])),
        "summary": replay.get("summary", {}),
        "artifacts": {
            "replay_report": ir16_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase16_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase16_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

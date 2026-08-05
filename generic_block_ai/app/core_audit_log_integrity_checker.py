"""
core_audit_log_integrity_checker.py - IR14

Integrity checker for IR12/IR13 audit logs in dry-run mode.
Only validates local artifacts and writes local reports.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR12_SCHEMA_VERSION = "ir12_core_decision_queue_v1"
IR13_SCHEMA_VERSION = "ir13_manual_approval_v1"
IR14_SCHEMA_VERSION = "ir14_audit_log_integrity_v1"

_QUEUE_REQUIRED_KEYS = {
    "event",
    "at",
    "queue_item_id",
    "source_task_id",
    "quality_gate_judgment",
    "queue_state",
    "execution_triggered",
    "external_write_executed",
    "production_release",
}

_MANUAL_REQUIRED_KEYS = {
    "event",
    "at",
    "source_task_id",
    "queue_item_id",
    "manual_event",
    "actor",
    "from",
    "to",
    "result",
    "execution_triggered",
    "external_write_executed",
    "production_release",
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


def _check_required_keys(
    entries: list[dict[str, Any]],
    required: set[str],
    *,
    label: str,
    failures: list[str],
) -> None:
    for idx, entry in enumerate(entries):
        missing = sorted(key for key in required if key not in entry)
        if missing:
            failures.append(f"{label}[{idx}] missing keys: {missing}")


def _check_no_time_reversal(
    entries: list[dict[str, Any]],
    *,
    label: str,
    failures: list[str],
) -> None:
    prev: datetime | None = None
    for idx, entry in enumerate(entries):
        at = str(entry.get("at", ""))
        try:
            current = _parse_iso8601(at)
        except ValueError:
            failures.append(f"{label}[{idx}] has invalid timestamp: {at}")
            continue
        if prev and current < prev:
            failures.append(f"{label}[{idx}] has time reversal")
        prev = current


def _extract_expected_queue_items(queue_report_paths: list[str]) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for path_str in queue_report_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        report = _read_json(path)
        if report.get("schema_version") != IR12_SCHEMA_VERSION:
            continue
        queue_item = report.get("queue_item", {})
        queue_item_id = str(queue_item.get("queue_item_id", ""))
        if not queue_item_id:
            continue
        expected[queue_item_id] = {
            "path": str(path),
            "quality_gate_judgment": queue_item.get("quality_gate_judgment"),
            "queue_state": queue_item.get("queue_state"),
        }
    return expected


def _check_abort_lock_tampering(
    *,
    expected_queue_items: dict[str, dict[str, Any]],
    manual_entries: list[dict[str, Any]],
    failures: list[str],
) -> None:
    abort_ids = {
        queue_id
        for queue_id, info in expected_queue_items.items()
        if str(info.get("quality_gate_judgment")) == "ABORT"
        or str(info.get("queue_state")) == "ABORT_EVIDENCE_LOCKED"
    }

    for idx, entry in enumerate(manual_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        if queue_item_id not in abort_ids:
            continue

        src_state = str(entry.get("from", ""))
        dst_state = str(entry.get("to", ""))
        result = str(entry.get("result", ""))
        manual_event = str(entry.get("manual_event", ""))

        if src_state == "ABORT_EVIDENCE_LOCKED" and dst_state != "ABORT_EVIDENCE_LOCKED":
            failures.append(f"manual_log[{idx}] tamper detected: ABORT lock state changed")
        if manual_event == "APPROVE" and result == "PASS":
            failures.append(f"manual_log[{idx}] tamper detected: ABORT approve was accepted")


def _check_queue_manual_alignment(
    *,
    queue_entries: list[dict[str, Any]],
    manual_entries: list[dict[str, Any]],
    failures: list[str],
) -> None:
    queue_state_map: dict[str, str] = {}
    seen_queue_ids: set[str] = set()

    for idx, entry in enumerate(queue_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        queue_state = str(entry.get("queue_state", ""))
        if not queue_item_id:
            continue
        if queue_item_id in seen_queue_ids:
            failures.append(f"queue_log[{idx}] duplicate queue_item_id detected: {queue_item_id}")
        seen_queue_ids.add(queue_item_id)
        queue_state_map[queue_item_id] = queue_state

    seen_manual_fingerprints: set[tuple[str, str, str, str]] = set()

    for idx, entry in enumerate(manual_entries):
        queue_item_id = str(entry.get("queue_item_id", ""))
        if queue_item_id not in queue_state_map:
            failures.append(f"manual_log[{idx}] queue_item_id not found in queue_log: {queue_item_id}")
            continue

        fingerprint = (
            queue_item_id,
            str(entry.get("manual_event", "")),
            str(entry.get("actor", "")),
            str(entry.get("at", "")),
        )
        if fingerprint in seen_manual_fingerprints:
            failures.append(f"manual_log[{idx}] duplicate manual event detected")
        seen_manual_fingerprints.add(fingerprint)

        expected_from = queue_state_map[queue_item_id]
        actual_from = str(entry.get("from", ""))
        actual_to = str(entry.get("to", ""))
        result = str(entry.get("result", ""))

        if actual_from != expected_from:
            failures.append(f"manual_log[{idx}] from-state mismatch for {queue_item_id}")

        if result == "PASS":
            queue_state_map[queue_item_id] = actual_to
        else:
            if actual_to != actual_from:
                failures.append(f"manual_log[{idx}] FAIL event changed state for {queue_item_id}")


def run_ir14_audit_log_integrity_check(
    *,
    base_path: Path,
    source_task_id: str,
    ir12_audit_log_path: Path | None = None,
    ir13_audit_log_path: Path | None = None,
    ir12_queue_report_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR14-T1/T2/T3/T4
    Validate audit log integrity across IR12 queue and IR13 manual approval logs.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    queue_log_path = ir12_audit_log_path or (reports_dir / "ir12_core_decision_queue_audit.log")
    manual_log_path = ir13_audit_log_path or (reports_dir / "ir13_manual_approval_audit.log")

    queue_entries = _read_jsonl(queue_log_path)
    manual_entries = _read_jsonl(manual_log_path)

    queue_report_paths = ir12_queue_report_paths or [
        str(path)
        for path in sorted(reports_dir.glob("ir12_core_decision_queue_*.json"))
        if path.name != "ir12_core_decision_queue_audit.log"
    ]
    expected_queue_items = _extract_expected_queue_items(queue_report_paths)

    failures: list[str] = []
    warnings: list[str] = []

    if not queue_entries:
        failures.append("queue audit log is empty")
    if not manual_entries:
        warnings.append("manual approval audit log is empty")

    _check_required_keys(queue_entries, _QUEUE_REQUIRED_KEYS, label="queue_log", failures=failures)
    _check_required_keys(manual_entries, _MANUAL_REQUIRED_KEYS, label="manual_log", failures=failures)

    _check_no_time_reversal(queue_entries, label="queue_log", failures=failures)
    _check_no_time_reversal(manual_entries, label="manual_log", failures=failures)

    actual_queue_ids = {str(entry.get("queue_item_id", "")) for entry in queue_entries if entry.get("queue_item_id")}
    expected_queue_ids = set(expected_queue_items.keys())
    missing_queue_ids = sorted(queue_id for queue_id in expected_queue_ids if queue_id not in actual_queue_ids)
    if missing_queue_ids:
        failures.append(f"missing queue_item_id in queue_log: {missing_queue_ids}")

    _check_queue_manual_alignment(
        queue_entries=queue_entries,
        manual_entries=manual_entries,
        failures=failures,
    )

    _check_abort_lock_tampering(
        expected_queue_items=expected_queue_items,
        manual_entries=manual_entries,
        failures=failures,
    )

    result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR14_SCHEMA_VERSION,
        "phase": "IR14",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "queue_log_entries": len(queue_entries),
            "manual_log_entries": len(manual_entries),
            "expected_queue_items": len(expected_queue_items),
            "missing_queue_items": len(missing_queue_ids),
            "abort_tamper_checks": "completed",
            "queue_manual_alignment": "checked",
        },
        "artifacts": {
            "ir12_audit_log": str(queue_log_path),
            "ir13_audit_log": str(manual_log_path),
            "ir12_queue_reports": queue_report_paths,
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
    out_path = reports_dir / f"ir14_audit_log_integrity_report_{task_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "integrity_report": report,
        "external_write_executed": False,
    }


def write_ir14_completion_report(
    *,
    base_path: Path,
    ir14_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR14-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}
    integrity = ir14_output.get("integrity_report", {}) if isinstance(ir14_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 14",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR14_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": integrity.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(integrity.get("validation_failed_checks", [])),
        "validation_warning_count": len(integrity.get("validation_warnings", [])),
        "artifacts": {
            "integrity_report": ir14_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase14_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase14_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

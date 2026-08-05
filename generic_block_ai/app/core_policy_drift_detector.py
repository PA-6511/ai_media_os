"""
core_policy_drift_detector.py - IR19

Detect policy drift between IR17 role_policy_change_audit and IR15 role guard usage.
Validates chronological policy usage, hash consistency, and audit chain continuity.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR15_SCHEMA_VERSION = "ir15_manual_event_role_guard_v1"
IR19_SCHEMA_VERSION = "ir19_policy_drift_detector_v1"


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


def _load_ir15_reports(paths: list[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        data = _read_json(path)
        if data.get("schema_version") != IR15_SCHEMA_VERSION:
            continue
        reports.append(data)
    reports.sort(key=lambda item: str(item.get("generated_at", "")))
    return reports


def _validate_audit_chain(entries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    normalized: list[dict[str, Any]] = []

    for idx, entry in enumerate(entries):
        at = str(entry.get("at", ""))
        new_hash = str(entry.get("new_role_policy_hash", ""))
        prev_hash = entry.get("previous_role_policy_hash")

        if not at:
            failures.append(f"audit[{idx}] missing at")
            continue
        if not new_hash:
            failures.append(f"audit[{idx}] missing new_role_policy_hash")
            continue

        try:
            parsed_at = _parse_iso8601(at)
        except ValueError:
            failures.append(f"audit[{idx}] invalid timestamp")
            continue

        normalized.append(
            {
                "at": at,
                "parsed_at": parsed_at,
                "new_role_policy_hash": new_hash,
                "previous_role_policy_hash": prev_hash,
                "change_type": str(entry.get("change_type", "")),
            }
        )

    normalized.sort(key=lambda item: item["parsed_at"])

    for idx, entry in enumerate(normalized):
        prev_hash = entry.get("previous_role_policy_hash")
        if idx == 0:
            continue
        prev_new = normalized[idx - 1]["new_role_policy_hash"]
        if prev_hash != prev_new:
            failures.append(
                "audit chain break at index "
                f"{idx}: previous_role_policy_hash={prev_hash!r} expected {prev_new!r}"
            )

    return failures, normalized


def _expected_hash_for_time(audit_entries: list[dict[str, Any]], at: datetime) -> str | None:
    candidate: str | None = None
    for entry in audit_entries:
        if entry["parsed_at"] <= at:
            candidate = str(entry["new_role_policy_hash"])
        else:
            break
    return candidate


def run_ir19_policy_drift_detector_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir17_change_audit_path: Path | None = None,
    ir15_report_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR19-T1/T2/T3/T4
    Detect unrecorded policy usage, hash mismatch, and audit gaps.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    audit_path = ir17_change_audit_path or (reports_dir / "ir17_role_policy_change_audit.log")
    audit_entries_raw = _read_jsonl(audit_path)
    audit_failures, audit_entries = _validate_audit_chain(audit_entries_raw)

    ir15_paths = ir15_report_paths or [
        str(path) for path in sorted(reports_dir.glob("ir15_manual_event_role_guard_*.json"))
    ]
    ir15_reports = _load_ir15_reports(ir15_paths)

    failures: list[str] = [*audit_failures]
    warnings: list[str] = []

    if not audit_entries:
        failures.append("ir17 role policy change audit is empty")

    known_hashes = {str(entry["new_role_policy_hash"]) for entry in audit_entries}

    unrecorded_policy_use: list[dict[str, str]] = []
    timeline_hash_mismatches: list[dict[str, str]] = []

    for idx, report in enumerate(ir15_reports):
        report_hash = str(report.get("role_policy_hash", ""))
        generated_at = str(report.get("generated_at", ""))
        source = str(report.get("source_task_id", f"ir15[{idx}]"))

        if not report_hash:
            failures.append(f"ir15[{idx}] missing role_policy_hash")
            continue

        if report_hash not in known_hashes:
            failures.append(f"ir15[{idx}] unrecorded policy hash used")
            unrecorded_policy_use.append(
                {
                    "source_task_id": source,
                    "generated_at": generated_at,
                    "role_policy_hash": report_hash,
                }
            )

        try:
            report_time = _parse_iso8601(generated_at)
        except ValueError:
            failures.append(f"ir15[{idx}] invalid generated_at")
            continue

        expected_hash = _expected_hash_for_time(audit_entries, report_time)
        if expected_hash is None:
            failures.append(f"ir15[{idx}] audit gap: no policy version existed at report time")
            timeline_hash_mismatches.append(
                {
                    "source_task_id": source,
                    "generated_at": generated_at,
                    "expected_role_policy_hash": "NONE",
                    "actual_role_policy_hash": report_hash,
                }
            )
            continue

        if report_hash != expected_hash:
            failures.append(f"ir15[{idx}] timeline hash mismatch")
            timeline_hash_mismatches.append(
                {
                    "source_task_id": source,
                    "generated_at": generated_at,
                    "expected_role_policy_hash": expected_hash,
                    "actual_role_policy_hash": report_hash,
                }
            )

    if not ir15_reports:
        warnings.append("ir15 role guard reports are empty")

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR19_SCHEMA_VERSION,
        "phase": "IR19",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "ir17_audit_entries": len(audit_entries),
            "ir15_reports_checked": len(ir15_reports),
            "known_policy_hashes": len(known_hashes),
            "unrecorded_policy_use_count": len(unrecorded_policy_use),
            "timeline_hash_mismatch_count": len(timeline_hash_mismatches),
            "audit_chain_break_count": len(audit_failures),
        },
        "unrecorded_policy_use": unrecorded_policy_use,
        "timeline_hash_mismatches": timeline_hash_mismatches,
        "artifacts": {
            "ir17_change_audit_log": str(audit_path),
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
    out_path = reports_dir / f"ir19_policy_drift_detector_report_{task_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "drift_report": report,
        "external_write_executed": False,
    }


def write_ir19_completion_report(
    *,
    base_path: Path,
    ir19_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR19-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    drift = ir19_output.get("drift_report", {}) if isinstance(ir19_output, dict) else {}
    summary = drift.get("summary", {})

    completion = {
        "phase": "Implementation Restart Phase 19",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR19_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": drift.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(drift.get("validation_failed_checks", [])),
        "validation_warning_count": len(drift.get("validation_warnings", [])),
        "summary": summary,
        "artifacts": {
            "drift_report": ir19_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase19_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase19_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

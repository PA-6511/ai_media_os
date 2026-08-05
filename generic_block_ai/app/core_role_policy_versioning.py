"""
core_role_policy_versioning.py - IR17

Track role policy versions, hashes, and change audit entries.
Cross-check IR15 role guard reports against the active policy hash.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core_manual_event_role_guard import DEFAULT_ROLE_POLICY

IR15_SCHEMA_VERSION = "ir15_manual_event_role_guard_v1"
IR17_SCHEMA_VERSION = "ir17_role_policy_versioning_v1"
ROLE_POLICY_SCHEMA_VERSION = "ir17_role_policy_v1"

REQUIRED_EVENTS = ("APPROVE", "REJECT", "REQUEST_FIX")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _normalize_policy(role_policy: dict[str, list[str]] | None) -> dict[str, list[str]]:
    source = role_policy if isinstance(role_policy, dict) else DEFAULT_ROLE_POLICY
    normalized: dict[str, list[str]] = {}

    for event in REQUIRED_EVENTS:
        raw_roles = source.get(event, [])
        if not isinstance(raw_roles, list):
            raw_roles = []
        cleaned: list[str] = []
        for role in raw_roles:
            norm = str(role).strip().lower()
            if not norm or norm in cleaned:
                continue
            cleaned.append(norm)
        normalized[event] = cleaned

    return normalized


def _policy_hash(policy: dict[str, list[str]]) -> str:
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_role_policy_schema(role_policy: dict[str, list[str]] | None) -> dict[str, Any]:
    """
    IR17-T1
    Validate role policy schema.
    """
    failed: list[str] = []
    warnings: list[str] = []

    if role_policy is not None and not isinstance(role_policy, dict):
        failed.append("role_policy must be a dictionary")

    normalized = _normalize_policy(role_policy)

    for event in REQUIRED_EVENTS:
        roles = normalized.get(event, [])
        if not roles:
            failed.append(f"role_policy.{event} must contain at least one role")

    result = "FAIL" if failed else ("WARN" if warnings else "PASS")
    return {
        "result": result,
        "failed_checks": failed,
        "warnings": warnings,
        "normalized_policy": normalized,
    }


def _append_change_audit(log_path: Path, entry: dict[str, Any]) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _last_change_entry(log_path: Path) -> dict[str, Any] | None:
    if not log_path.exists():
        return None
    lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    return json.loads(lines[-1])


def _load_ir15_reports(paths: list[str]) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != IR15_SCHEMA_VERSION:
            continue
        loaded.append(report)
    return loaded


def _check_ir15_hash_alignment(
    *,
    ir15_reports: list[dict[str, Any]],
    policy_hash: str,
    policy: dict[str, list[str]],
) -> dict[str, Any]:
    failed: list[str] = []
    warnings: list[str] = []

    for idx, report in enumerate(ir15_reports):
        event = str(report.get("manual_event", "")).upper()
        allowed_roles = report.get("allowed_roles", [])
        report_hash = str(report.get("role_policy_hash", ""))

        expected_roles = policy.get(event, [])
        if sorted(str(r).lower() for r in allowed_roles) != sorted(expected_roles):
            failed.append(f"ir15[{idx}] allowed_roles mismatch for event {event}")

        if not report_hash:
            failed.append(f"ir15[{idx}] missing role_policy_hash")
        elif report_hash != policy_hash:
            failed.append(f"ir15[{idx}] role_policy_hash mismatch")

    result = "FAIL" if failed else ("WARN" if warnings else "PASS")
    return {
        "result": result,
        "failed_checks": failed,
        "warnings": warnings,
        "checked_reports": len(ir15_reports),
    }


def run_ir17_role_policy_versioning_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    role_policy: dict[str, list[str]] | None = None,
    ir15_report_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR17-T1/T2/T3/T4
    Validate role policy schema, generate policy hash, emit change audit,
    and cross-check against IR15 role guard reports.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    schema_validation = validate_role_policy_schema(role_policy)
    policy = schema_validation["normalized_policy"]
    policy_hash = _policy_hash(policy)

    audit_log_path = reports_dir / "ir17_role_policy_change_audit.log"
    previous = _last_change_entry(audit_log_path)
    previous_hash = str(previous.get("new_role_policy_hash", "")) if previous else None

    if previous_hash is None:
        change_type = "initial"
    elif previous_hash == policy_hash:
        change_type = "unchanged"
    else:
        change_type = "updated"

    change_audit_entry = {
        "event": "role_policy_version_recorded",
        "at": _now_iso(),
        "source_task_id": source_task_id,
        "role_policy_schema_version": ROLE_POLICY_SCHEMA_VERSION,
        "previous_role_policy_hash": previous_hash,
        "new_role_policy_hash": policy_hash,
        "change_type": change_type,
        "external_write_executed": False,
        "production_release": False,
    }
    _append_change_audit(audit_log_path, change_audit_entry)

    ir15_paths = ir15_report_paths or [
        str(path) for path in sorted(reports_dir.glob("ir15_manual_event_role_guard_*.json"))
    ]
    ir15_reports = _load_ir15_reports(ir15_paths)
    ir15_alignment = _check_ir15_hash_alignment(
        ir15_reports=ir15_reports,
        policy_hash=policy_hash,
        policy=policy,
    )

    failures = [*schema_validation["failed_checks"], *ir15_alignment["failed_checks"]]
    warnings = [*schema_validation["warnings"], *ir15_alignment["warnings"]]
    result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR17_SCHEMA_VERSION,
        "phase": "IR17",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "role_policy_schema_version": ROLE_POLICY_SCHEMA_VERSION,
        "role_policy": policy,
        "role_policy_hash": policy_hash,
        "change_audit": change_audit_entry,
        "validation_result": result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "ir15_alignment": ir15_alignment,
        "artifacts": {
            "role_policy_change_audit_log": str(audit_log_path),
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
    out_path = reports_dir / f"ir17_role_policy_versioning_report_{task_key}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "versioning_report": report,
        "external_write_executed": False,
    }


def write_ir17_completion_report(
    *,
    base_path: Path,
    ir17_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR17-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    versioning = ir17_output.get("versioning_report", {}) if isinstance(ir17_output, dict) else {}
    alignment = versioning.get("ir15_alignment", {})

    completion = {
        "phase": "Implementation Restart Phase 17",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR17_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": versioning.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(versioning.get("validation_failed_checks", [])),
        "validation_warning_count": len(versioning.get("validation_warnings", [])),
        "role_policy_hash": versioning.get("role_policy_hash", ""),
        "ir15_alignment_checked_reports": alignment.get("checked_reports", 0),
        "artifacts": {
            "versioning_report": ir17_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase17_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase17_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

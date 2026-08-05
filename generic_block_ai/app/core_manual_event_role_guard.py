"""
core_manual_event_role_guard.py - IR15

Role guard for IR13 manual approval events in dry-run mode.
Validates whether the actor role is authorized for each event.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR13_SCHEMA_VERSION = "ir13_manual_approval_v1"
IR15_SCHEMA_VERSION = "ir15_manual_event_role_guard_v1"

VALID_EVENTS = {"APPROVE", "REJECT", "REQUEST_FIX"}

DEFAULT_ROLE_POLICY: dict[str, list[str]] = {
    "APPROVE": ["approver", "senior_reviewer", "admin"],
    "REJECT": ["reviewer", "approver", "senior_reviewer", "admin"],
    "REQUEST_FIX": ["reviewer", "approver", "senior_reviewer", "admin"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _normalize_policy(policy: dict[str, list[str]] | None) -> dict[str, list[str]]:
    merged = {key: list(value) for key, value in DEFAULT_ROLE_POLICY.items()}
    if not isinstance(policy, dict):
        return merged
    for event, roles in policy.items():
        normalized_event = str(event).upper()
        if normalized_event not in VALID_EVENTS:
            continue
        if not isinstance(roles, list):
            continue
        normalized_roles = [str(role).strip().lower() for role in roles if str(role).strip()]
        merged[normalized_event] = normalized_roles
    return merged


def _policy_hash(policy: dict[str, list[str]]) -> str:
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_role_guard_input(
    *,
    ir13_report: dict[str, Any],
    actor_roles: dict[str, str],
    role_policy: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    IR15-T1/T2
    Validate IR13 report, actor role schema, and event role policy.
    """
    failed: list[str] = []
    warnings: list[str] = []

    if ir13_report.get("schema_version") != IR13_SCHEMA_VERSION:
        failed.append(f"ir13_report.schema_version must be {IR13_SCHEMA_VERSION}")

    event = str(ir13_report.get("manual_event", "")).upper()
    if event not in VALID_EVENTS:
        failed.append(f"manual_event must be one of {sorted(VALID_EVENTS)}")

    actor = str(ir13_report.get("actor", "")).strip()
    if not actor:
        failed.append("actor is required")

    if not isinstance(actor_roles, dict) or not actor_roles:
        failed.append("actor_roles must be a non-empty mapping")

    queue_item = ir13_report.get("queue_item", {})
    queue_state = str(queue_item.get("queue_state", ""))
    quality_gate_judgment = str(queue_item.get("quality_gate_judgment", ""))

    execution_policy = ir13_report.get("execution_policy", {})
    if execution_policy.get("execute") is not False:
        failed.append("execution_policy.execute must be false")

    safeguards = ir13_report.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("safeguards.external_write_executed must be false")
    if safeguards.get("production_release") is not False:
        failed.append("safeguards.production_release must be false")

    policy = _normalize_policy(role_policy)

    actor_role = str(actor_roles.get(actor, "")).strip().lower()
    if actor and not actor_role:
        failed.append("actor role is not defined in actor_roles")

    allowed_roles = policy.get(event, [])
    if event in VALID_EVENTS and not allowed_roles:
        failed.append(f"role policy for event {event} is empty")

    if actor_role and allowed_roles and actor_role not in allowed_roles:
        failed.append(f"actor role '{actor_role}' is not allowed for event {event}")

    if queue_state == "ABORT_EVIDENCE_LOCKED" or quality_gate_judgment == "ABORT":
        failed.append("ABORT evidence lock override is prohibited")

    if ir13_report.get("event_validation_result") == "FAIL":
        warnings.append("upstream ir13 event validation is FAIL")

    result = "FAIL" if failed else ("WARN" if warnings else "PASS")

    return {
        "result": result,
        "failed_checks": failed,
        "warnings": warnings,
        "manual_event": event,
        "actor": actor,
        "actor_role": actor_role,
        "allowed_roles": allowed_roles,
        "queue_state": queue_state,
        "quality_gate_judgment": quality_gate_judgment,
        "resolved_role_policy": policy,
    }


def run_ir15_manual_event_role_guard_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir13_report: dict[str, Any],
    actor_roles: dict[str, str],
    role_policy: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    IR15-T3/T4
    Evaluate role authorization and block override attempts on ABORT lock.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    validation = validate_role_guard_input(
        ir13_report=ir13_report,
        actor_roles=actor_roles,
        role_policy=role_policy,
    )

    result_report = {
        "schema_version": IR15_SCHEMA_VERSION,
        "phase": "IR15",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "manual_event": validation["manual_event"],
        "actor": validation["actor"],
        "actor_role": validation["actor_role"],
        "allowed_roles": validation["allowed_roles"],
        "role_policy": validation["resolved_role_policy"],
        "role_policy_hash": _policy_hash(validation["resolved_role_policy"]),
        "queue_state": validation["queue_state"],
        "quality_gate_judgment": validation["quality_gate_judgment"],
        "role_guard_result": validation["result"],
        "role_guard_failed_checks": validation["failed_checks"],
        "role_guard_warnings": validation["warnings"],
        "upstream": {
            "ir13_schema_version": ir13_report.get("schema_version"),
            "ir13_event_validation_result": ir13_report.get("event_validation_result"),
            "ir13_path_hint": ir13_report.get("source_task_id"),
        },
        "execution_policy": {
            "execute": False,
            "reason": "ir15_role_guard_dryrun_only",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    task_key = _safe(source_task_id)
    path = reports_dir / f"ir15_manual_event_role_guard_{task_key}.json"
    path.write_text(json.dumps(result_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(path),
        "ir15_report": result_report,
        "external_write_executed": False,
    }


def write_ir15_completion_report(
    *,
    base_path: Path,
    ir15_outputs: list[dict[str, Any]],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR15-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    result_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    artifact_paths: list[str] = []
    abort_override_blocked = False

    for output in ir15_outputs:
        if not isinstance(output, dict):
            continue
        artifact_paths.append(output.get("path", "UNKNOWN"))
        report = output.get("ir15_report", {})

        result = str(report.get("role_guard_result", "UNKNOWN"))
        result_counts[result] = result_counts.get(result, 0) + 1

        event = str(report.get("manual_event", "UNKNOWN"))
        event_counts[event] = event_counts.get(event, 0) + 1

        role = str(report.get("actor_role", "UNKNOWN"))
        role_counts[role] = role_counts.get(role, 0) + 1

        if any("ABORT evidence lock override is prohibited" in item for item in report.get("role_guard_failed_checks", [])):
            abort_override_blocked = True

    completion = {
        "phase": "Implementation Restart Phase 15",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR15_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "summary": {
            "role_guard_result_counts": result_counts,
            "manual_event_counts": event_counts,
            "actor_role_counts": role_counts,
            "abort_override_blocked": abort_override_blocked,
            "execution_triggered": False,
        },
        "artifacts": {
            "role_guard_reports": artifact_paths,
            "completion_report": "reports/implementation_restart_phase15_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase15_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

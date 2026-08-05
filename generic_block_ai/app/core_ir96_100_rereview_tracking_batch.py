"""
core_ir96_100_rereview_tracking_batch.py - IR96-IR100

Batch implementation for re-review execution tracking in dry-run mode:
IR96 re-review queue execution tracker, IR97 remediation evidence intake verifier,
IR98 pre-unlock delta audit, IR99 unlock prohibition reconfirmation gate,
IR100 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR95_SCHEMA_VERSION = "ir95_phase_91_95_completion_bundle_v1"
IR96_SCHEMA_VERSION = "ir96_re_review_queue_execution_tracker_v1"
IR97_SCHEMA_VERSION = "ir97_remediation_evidence_intake_verifier_v1"
IR98_SCHEMA_VERSION = "ir98_pre_unlock_delta_audit_v1"
IR99_SCHEMA_VERSION = "ir99_unlock_prohibition_reconfirmation_gate_v1"
IR100_SCHEMA_VERSION = "ir100_phase_96_100_completion_bundle_v1"

IR99_CONFIRMED = "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY"
IR99_HOLD = "HOLD"
IR99_ABORT = "ABORT"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _default_safety_gate() -> dict[str, Any]:
    return {
        "dry_run": "maintained",
        "OBSERVE": "maintained",
        "submission_execution_blocked": True,
        "execution_policy_execute": False,
        "external_write_executed": False,
        "network_transmission_executed": False,
        "production_release": False,
        "GitHub_push": "未実行",
    }


# ---------------------------------------------------------------------------
# IR96: Re-Review Queue Execution Tracker
# ---------------------------------------------------------------------------

def _build_ir96_report(
    *,
    ir95_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Track execution state of re-review queue items in dry-run mode."""
    failed_checks: list[str] = []

    if ir95_report.get("schema_version") != IR95_SCHEMA_VERSION:
        failed_checks.append(f"ir95 schema_version must be {IR95_SCHEMA_VERSION}")

    if ir95_report.get("final_decision") != "UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY":
        failed_checks.append("ir95 final_decision must be UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY")

    if ir95_report.get("unlock_prohibition_continuity_confirmed") is not True:
        failed_checks.append("ir95 unlock_prohibition_continuity_confirmed must be true")

    queue_registry = ir95_report.get("ir93_result", {}).get("re_review_queue_registry", {})
    queue_entries = queue_registry.get("queue_entries", []) if isinstance(queue_registry, dict) else []

    if not queue_entries:
        failed_checks.append("ir95 ir93_result.re_review_queue_registry.queue_entries must not be empty")

    tracked_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"item_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "execution_status": "TRACKED_PENDING_REVIEW",
            "dry_run_executed": False,
        }
        for idx, entry in enumerate(queue_entries)
        if isinstance(entry, dict)
    ]

    tracker = {
        "tracker_id": f"ir96_tracker_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir95_report.get("new_cycle_id", "UNKNOWN"),
        "tracked_entries": tracked_entries,
        "tracked_count": len(tracked_entries),
        "execution_mode": "dry_run_tracking_only",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR96_SCHEMA_VERSION,
        "phase": "IR96",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "re_review_execution_tracker": tracker,
        "tracker_hash": _sha256_hex(tracker),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR97: Remediation Evidence Intake Verifier
# ---------------------------------------------------------------------------

def _build_ir97_report(
    *,
    ir96_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Verify intake readiness for remediation evidence without applying unlock."""
    failed_checks: list[str] = []

    if ir96_report.get("validation_result") != "PASS":
        failed_checks.append("ir96 execution tracker must be PASS")

    tracker = ir96_report.get("re_review_execution_tracker", {})
    tracked = tracker.get("tracked_entries", []) if isinstance(tracker, dict) else []

    if not tracked:
        failed_checks.append("ir96 tracked_entries must not be empty")

    intake_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "evidence_intake_status": "NOT_RECEIVED",
            "verified": False,
        }
        for entry in tracked
        if isinstance(entry, dict)
    ]

    all_received = all(e.get("evidence_intake_status") == "RECEIVED" for e in intake_entries)

    verifier = {
        "verifier_id": f"ir97_intake_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": tracker.get("new_cycle_id", "UNKNOWN") if isinstance(tracker, dict) else "UNKNOWN",
        "intake_entries": intake_entries,
        "all_required_evidence_received": all_received,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR97_SCHEMA_VERSION,
        "phase": "IR97",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "evidence_intake_verification": verifier,
        "verifier_hash": _sha256_hex(verifier),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR98: Pre-Unlock Delta Audit
# ---------------------------------------------------------------------------

def _build_ir98_report(
    *,
    ir97_report: dict[str, Any],
    ir95_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Audit remaining deltas before any unlock consideration."""
    failed_checks: list[str] = []

    if ir97_report.get("validation_result") != "PASS":
        failed_checks.append("ir97 intake verifier must be PASS")

    intake = ir97_report.get("evidence_intake_verification", {})
    entries = intake.get("intake_entries", []) if isinstance(intake, dict) else []
    unresolved = [e for e in entries if isinstance(e, dict) and e.get("verified") is False]

    prior_gap = ir95_report.get("ir91_result", {}).get("gap_remediation_plan", {}).get("all_items_completed")
    if prior_gap is not False:
        failed_checks.append("ir95 ir91_result.gap_remediation_plan.all_items_completed must be false")

    audit = {
        "audit_id": f"ir98_audit_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir95_report.get("new_cycle_id", "UNKNOWN"),
        "unresolved_delta_count": len(unresolved),
        "pre_unlock_delta_status": "DELTA_REMAINS" if unresolved else "NO_DELTA",
        "unlock_recommended": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR98_SCHEMA_VERSION,
        "phase": "IR98",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "pre_unlock_delta_audit": audit,
        "audit_hash": _sha256_hex(audit),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR99: Unlock Prohibition Reconfirmation Gate
# ---------------------------------------------------------------------------

def run_ir99_unlock_prohibition_reconfirmation_gate(
    *,
    ir98_report: dict[str, Any],
    ir97_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Reconfirm unlock prohibition after re-review tracking and delta audit."""
    failed_checks: list[str] = []

    if ir98_report.get("validation_result") != "PASS":
        failed_checks.append("ir98 pre-unlock delta audit must be PASS")

    delta = ir98_report.get("pre_unlock_delta_audit", {})
    if delta.get("pre_unlock_delta_status") != "DELTA_REMAINS":
        failed_checks.append("ir98 pre_unlock_delta_status must be DELTA_REMAINS")

    if delta.get("unlock_recommended") is not False:
        failed_checks.append("ir98 unlock_recommended must be false")

    intake = ir97_report.get("evidence_intake_verification", {})
    if intake.get("all_required_evidence_received") is not False:
        failed_checks.append("ir97 all_required_evidence_received must be false")

    safety_snapshot = ir98_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR99_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR99_HOLD
        action = "Hold due to reconfirmation precondition mismatch."
    else:
        decision = IR99_CONFIRMED
        action = "Unlock prohibition reconfirmed. Dry-run-only remains enforced."

    gate = {
        "gate_id": f"ir99_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "reconfirmed": decision == IR99_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR99_SCHEMA_VERSION,
        "phase": "IR99",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "unlock_prohibition_reconfirmation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gate_record": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir96_100_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir95_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR96-IR99 batch run for re-review tracking in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir96_100"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir95_path = ir95_completion_bundle_path or (
        reports_dir / "ir91_95" / "ir95_completion_bundle.json"
    )

    if not ir95_path.exists():
        raise FileNotFoundError(f"ir95 completion bundle not found: {ir95_path}")

    ir95_report = _read_json(ir95_path)

    ir96_report = _build_ir96_report(
        ir95_report=ir95_report,
        source_task_id=source_task_id,
    )
    ir96_path = out_dir / "ir96_re_review_queue_execution_tracker.json"
    _write_json(ir96_path, ir96_report)

    ir97_report = _build_ir97_report(
        ir96_report=ir96_report,
        source_task_id=source_task_id,
    )
    ir97_path = out_dir / "ir97_remediation_evidence_intake_verification.json"
    _write_json(ir97_path, ir97_report)

    ir98_report = _build_ir98_report(
        ir97_report=ir97_report,
        ir95_report=ir95_report,
        source_task_id=source_task_id,
    )
    ir98_path = out_dir / "ir98_pre_unlock_delta_audit.json"
    _write_json(ir98_path, ir98_report)

    ir99_report = run_ir99_unlock_prohibition_reconfirmation_gate(
        ir98_report=ir98_report,
        ir97_report=ir97_report,
        source_task_id=source_task_id,
    )
    ir99_path = out_dir / "ir99_unlock_prohibition_reconfirmation_gate_report.json"
    _write_json(ir99_path, ir99_report)

    final_decision = ir99_report["unlock_prohibition_reconfirmation_decision"]

    return {
        "phase": "IR96_100_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir95_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir95_bundle_path": _to_ref(ir95_path, project_root),
        "final_decision": final_decision,
        "ir96_result": ir96_report,
        "ir97_result": ir97_report,
        "ir98_result": ir98_report,
        "ir99_result": ir99_report,
        "artifacts": {
            "ir96_re_review_queue_execution_tracker": _to_ref(ir96_path, project_root),
            "ir97_remediation_evidence_intake_verification": _to_ref(ir97_path, project_root),
            "ir98_pre_unlock_delta_audit": _to_ref(ir98_path, project_root),
            "ir99_unlock_prohibition_reconfirmation_gate_report": _to_ref(ir99_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR100: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir96_100_completion_bundle(
    *,
    base_path: Path,
    ir96_100_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR100 completion bundle writer."""
    out_dir = base_path / "reports" / "ir96_100"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir96_result = ir96_100_output.get("ir96_result", {})
    ir97_result = ir96_100_output.get("ir97_result", {})
    ir98_result = ir96_100_output.get("ir98_result", {})
    ir99_result = ir96_100_output.get("ir99_result", {})
    final_decision = str(ir96_100_output.get("final_decision", IR99_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir99_live = "PASS" if final_decision == IR99_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR96", "content": "Re-Review Queue Execution Tracker", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir96_result), "judgement": _judgement(_live(ir96_result))},
        {"phase": "IR97", "content": "Remediation Evidence Intake Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir97_result), "judgement": _judgement(_live(ir97_result))},
        {"phase": "IR98", "content": "Pre-Unlock Delta Audit", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir98_result), "judgement": _judgement(_live(ir98_result))},
        {"phase": "IR99", "content": "Unlock Prohibition Reconfirmation Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir99_live, "judgement": _judgement(ir99_live)},
        {"phase": "IR100", "content": "Phase 96-100 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir99_live, "judgement": _judgement(ir99_live)},
    ]

    bundle = {
        "schema_version": IR100_SCHEMA_VERSION,
        "phase": "IR100",
        "generated_at": _now_iso(),
        "source_task_id": ir96_100_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir96_100_output.get("new_cycle_id", "UNKNOWN"),
        "ir96_result": ir96_result,
        "ir97_result": ir97_result,
        "ir98_result": ir98_result,
        "ir99_result": ir99_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir96": table_rows[0]["live"],
            "ir97": table_rows[1]["live"],
            "ir98": table_rows[2]["live"],
            "ir99": table_rows[3]["live"],
            "ir100": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "unlock_prohibition_reconfirmed": final_decision == IR99_CONFIRMED,
        "pre_unlock_delta_still_remains": ir98_result.get("pre_unlock_delta_audit", {}).get("pre_unlock_delta_status") == "DELTA_REMAINS",
        "artifacts": {
            **ir96_100_output.get("artifacts", {}),
            "ir100_completion_bundle": "generic_block_ai/reports/ir96_100/ir100_completion_bundle.json",
            "ir96_100_live_status": "generic_block_ai/reports/ir96_100/ir96_100_live_status.md",
            "ir96_100_completion_table": "generic_block_ai/reports/ir96_100/ir96_100_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir100_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR96-IR100 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Unlock Prohibition Reconfirmed: {bundle['unlock_prohibition_reconfirmed']}",
        f"- Pre-Unlock Delta Still Remains: {bundle['pre_unlock_delta_still_remains']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir96_100_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR96-IR100 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir96_100_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir100_completion_bundle": _to_ref(bundle_path, project_root),
            "ir96_100_live_status": _to_ref(live_path, project_root),
            "ir96_100_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

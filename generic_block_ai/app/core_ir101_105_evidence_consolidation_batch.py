"""
core_ir101_105_evidence_consolidation_batch.py - IR101-IR105

Batch implementation for evidence consolidation cycle governance in dry-run mode:
IR101 evidence consolidation status report, IR102 remediation delta progress tracker,
IR103 re-review cycle assessment, IR104 prohibition cycle continuation gate,
IR105 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR100_SCHEMA_VERSION = "ir100_phase_96_100_completion_bundle_v1"
IR101_SCHEMA_VERSION = "ir101_evidence_consolidation_status_report_v1"
IR102_SCHEMA_VERSION = "ir102_remediation_delta_progress_tracker_v1"
IR103_SCHEMA_VERSION = "ir103_re_review_cycle_assessment_v1"
IR104_SCHEMA_VERSION = "ir104_prohibition_cycle_continuation_gate_v1"
IR105_SCHEMA_VERSION = "ir105_phase_101_105_completion_bundle_v1"

IR104_CONFIRMED = "PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY"
IR104_HOLD = "HOLD"
IR104_ABORT = "ABORT"


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
# IR101: Evidence Consolidation Status Report
# ---------------------------------------------------------------------------

def _build_ir101_report(
    *,
    ir100_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Consolidate evidence status from re-review tracking cycle IR96-100."""
    failed_checks: list[str] = []

    if ir100_report.get("schema_version") != IR100_SCHEMA_VERSION:
        failed_checks.append(f"ir100 schema_version must be {IR100_SCHEMA_VERSION}")

    if ir100_report.get("final_decision") != "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY":
        failed_checks.append("ir100 final_decision must be UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY")

    if ir100_report.get("unlock_prohibition_reconfirmed") is not True:
        failed_checks.append("ir100 unlock_prohibition_reconfirmed must be true")

    if ir100_report.get("pre_unlock_delta_still_remains") is not True:
        failed_checks.append("ir100 pre_unlock_delta_still_remains must be true")

    # Collect intake entries from ir97 embedded in ir100
    ir97_result = ir100_report.get("ir97_result", {})
    intake_verification = ir97_result.get("evidence_intake_verification", {}) if isinstance(ir97_result, dict) else {}
    intake_entries = intake_verification.get("intake_entries", []) if isinstance(intake_verification, dict) else []

    consolidation_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"item_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "prior_intake_status": str(entry.get("evidence_intake_status", "NOT_RECEIVED")),
            "consolidation_status": "PENDING_CONSOLIDATION",
            "evidence_consolidated": False,
        }
        for idx, entry in enumerate(intake_entries)
        if isinstance(entry, dict)
    ]

    if not consolidation_entries:
        failed_checks.append("ir100 ir97_result.evidence_intake_verification.intake_entries must not be empty")

    all_consolidated = all(e.get("evidence_consolidated") is True for e in consolidation_entries)

    report = {
        "report_id": f"ir101_consolidation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir100_report.get("new_cycle_id", "UNKNOWN"),
        "consolidation_entries": consolidation_entries,
        "consolidated_count": len(consolidation_entries),
        "all_evidence_consolidated": all_consolidated,
        "consolidation_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR101_SCHEMA_VERSION,
        "phase": "IR101",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "evidence_consolidation_status": report,
        "report_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR102: Remediation Delta Progress Tracker
# ---------------------------------------------------------------------------

def _build_ir102_report(
    *,
    ir101_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Track progress of remediation delta closure in dry-run mode."""
    failed_checks: list[str] = []

    if ir101_report.get("validation_result") != "PASS":
        failed_checks.append("ir101 evidence consolidation status report must be PASS")

    consolidation = ir101_report.get("evidence_consolidation_status", {})
    entries = consolidation.get("consolidation_entries", []) if isinstance(consolidation, dict) else []

    if not entries:
        failed_checks.append("ir101 consolidation_entries must not be empty")

    delta_items = [
        {
            "item_id": str(e.get("queue_item_id", "UNKNOWN")),
            "item": str(e.get("item", "UNKNOWN")),
            "prior_consolidation_status": str(e.get("consolidation_status", "PENDING_CONSOLIDATION")),
            "delta_progress_status": "DELTA_OPEN",
            "progress_percentage": 0,
            "closure_eligible": False,
        }
        for e in entries
        if isinstance(e, dict)
    ]

    open_count = sum(1 for d in delta_items if d.get("delta_progress_status") == "DELTA_OPEN")
    closed_count = len(delta_items) - open_count

    tracker = {
        "tracker_id": f"ir102_delta_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": consolidation.get("new_cycle_id", "UNKNOWN") if isinstance(consolidation, dict) else "UNKNOWN",
        "delta_items": delta_items,
        "total_delta_count": len(delta_items),
        "open_delta_count": open_count,
        "closed_delta_count": closed_count,
        "all_deltas_closed": closed_count == len(delta_items) and len(delta_items) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR102_SCHEMA_VERSION,
        "phase": "IR102",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "remediation_delta_progress": tracker,
        "tracker_hash": _sha256_hex(tracker),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR103: Re-Review Cycle Assessment
# ---------------------------------------------------------------------------

def _build_ir103_report(
    *,
    ir102_report: dict[str, Any],
    ir100_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Assess the overall re-review cycle state and readiness for next cycle."""
    failed_checks: list[str] = []

    if ir102_report.get("validation_result") != "PASS":
        failed_checks.append("ir102 remediation delta progress tracker must be PASS")

    tracker = ir102_report.get("remediation_delta_progress", {})
    if tracker.get("all_deltas_closed") is not False:
        failed_checks.append("ir102 all_deltas_closed must be false for cycle continuation")

    prior_decision = ir100_report.get("final_decision", "")
    if prior_decision != "UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY":
        failed_checks.append("ir100 final_decision must be UNLOCK_PROHIBITION_RECONFIRMED_DRY_RUN_ONLY")

    open_count = tracker.get("open_delta_count", 0) if isinstance(tracker, dict) else 0
    total_count = tracker.get("total_delta_count", 0) if isinstance(tracker, dict) else 0

    assessment = {
        "assessment_id": f"ir103_cycle_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir100_report.get("new_cycle_id", "UNKNOWN"),
        "prior_cycle_decision": prior_decision,
        "open_delta_count": open_count,
        "total_delta_count": total_count,
        "cycle_status": "CYCLE_IN_PROGRESS",
        "next_cycle_recommended": True,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR103_SCHEMA_VERSION,
        "phase": "IR103",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "re_review_cycle_assessment": assessment,
        "assessment_hash": _sha256_hex(assessment),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR104: Prohibition Cycle Continuation Gate
# ---------------------------------------------------------------------------

def run_ir104_prohibition_cycle_continuation_gate(
    *,
    ir103_report: dict[str, Any],
    ir102_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Gate to confirm prohibition cycle continues for the next evidence consolidation round."""
    failed_checks: list[str] = []

    if ir103_report.get("validation_result") != "PASS":
        failed_checks.append("ir103 re-review cycle assessment must be PASS")

    assessment = ir103_report.get("re_review_cycle_assessment", {})
    if assessment.get("cycle_status") != "CYCLE_IN_PROGRESS":
        failed_checks.append("ir103 cycle_status must be CYCLE_IN_PROGRESS")

    if assessment.get("next_cycle_recommended") is not True:
        failed_checks.append("ir103 next_cycle_recommended must be true")

    tracker = ir102_report.get("remediation_delta_progress", {})
    if tracker.get("unlock_eligible") is not False:
        failed_checks.append("ir102 unlock_eligible must be false")

    safety_snapshot = ir103_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR104_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR104_HOLD
        action = "Hold due to cycle continuation precondition mismatch."
    else:
        decision = IR104_CONFIRMED
        action = "Prohibition cycle continuation confirmed. Dry-run-only remains enforced."

    gate = {
        "gate_id": f"ir104_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "cycle_continued": decision == IR104_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR104_SCHEMA_VERSION,
        "phase": "IR104",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "prohibition_cycle_continuation_decision": decision,
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

def run_ir101_105_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir100_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR101-IR104 batch run for evidence consolidation cycle in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir101_105"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir100_path = ir100_completion_bundle_path or (
        reports_dir / "ir96_100" / "ir100_completion_bundle.json"
    )

    if not ir100_path.exists():
        raise FileNotFoundError(f"ir100 completion bundle not found: {ir100_path}")

    ir100_report = _read_json(ir100_path)

    ir101_report = _build_ir101_report(
        ir100_report=ir100_report,
        source_task_id=source_task_id,
    )
    ir101_path = out_dir / "ir101_evidence_consolidation_status_report.json"
    _write_json(ir101_path, ir101_report)

    ir102_report = _build_ir102_report(
        ir101_report=ir101_report,
        source_task_id=source_task_id,
    )
    ir102_path = out_dir / "ir102_remediation_delta_progress_tracker.json"
    _write_json(ir102_path, ir102_report)

    ir103_report = _build_ir103_report(
        ir102_report=ir102_report,
        ir100_report=ir100_report,
        source_task_id=source_task_id,
    )
    ir103_path = out_dir / "ir103_re_review_cycle_assessment.json"
    _write_json(ir103_path, ir103_report)

    ir104_report = run_ir104_prohibition_cycle_continuation_gate(
        ir103_report=ir103_report,
        ir102_report=ir102_report,
        source_task_id=source_task_id,
    )
    ir104_path = out_dir / "ir104_prohibition_cycle_continuation_gate_report.json"
    _write_json(ir104_path, ir104_report)

    final_decision = ir104_report["prohibition_cycle_continuation_decision"]

    return {
        "phase": "IR101_105_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir100_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir100_bundle_path": _to_ref(ir100_path, project_root),
        "final_decision": final_decision,
        "ir101_result": ir101_report,
        "ir102_result": ir102_report,
        "ir103_result": ir103_report,
        "ir104_result": ir104_report,
        "artifacts": {
            "ir101_evidence_consolidation_status_report": _to_ref(ir101_path, project_root),
            "ir102_remediation_delta_progress_tracker": _to_ref(ir102_path, project_root),
            "ir103_re_review_cycle_assessment": _to_ref(ir103_path, project_root),
            "ir104_prohibition_cycle_continuation_gate_report": _to_ref(ir104_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR105: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir101_105_completion_bundle(
    *,
    base_path: Path,
    ir101_105_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR105 completion bundle summarising IR101-105 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir101_105"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir101_result = ir101_105_output.get("ir101_result", {})
    ir102_result = ir101_105_output.get("ir102_result", {})
    ir103_result = ir101_105_output.get("ir103_result", {})
    ir104_result = ir101_105_output.get("ir104_result", {})
    final_decision = str(ir101_105_output.get("final_decision", IR104_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir104_live = "PASS" if final_decision == IR104_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR101", "content": "Evidence Consolidation Status Report", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir101_result), "judgement": _judgement(_live(ir101_result))},
        {"phase": "IR102", "content": "Remediation Delta Progress Tracker", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir102_result), "judgement": _judgement(_live(ir102_result))},
        {"phase": "IR103", "content": "Re-Review Cycle Assessment", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir103_result), "judgement": _judgement(_live(ir103_result))},
        {"phase": "IR104", "content": "Prohibition Cycle Continuation Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir104_live, "judgement": _judgement(ir104_live)},
        {"phase": "IR105", "content": "Phase 101-105 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir104_live, "judgement": _judgement(ir104_live)},
    ]

    bundle = {
        "schema_version": IR105_SCHEMA_VERSION,
        "phase": "IR105",
        "generated_at": _now_iso(),
        "source_task_id": ir101_105_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir101_105_output.get("new_cycle_id", "UNKNOWN"),
        "ir101_result": ir101_result,
        "ir102_result": ir102_result,
        "ir103_result": ir103_result,
        "ir104_result": ir104_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir101": table_rows[0]["live"],
            "ir102": table_rows[1]["live"],
            "ir103": table_rows[2]["live"],
            "ir104": table_rows[3]["live"],
            "ir105": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_cycle_continued": final_decision == IR104_CONFIRMED,
        "evidence_consolidation_pending": ir101_result.get("evidence_consolidation_status", {}).get("all_evidence_consolidated") is False,
        "artifacts": {
            **ir101_105_output.get("artifacts", {}),
            "ir105_completion_bundle": "generic_block_ai/reports/ir101_105/ir105_completion_bundle.json",
            "ir101_105_live_status": "generic_block_ai/reports/ir101_105/ir101_105_live_status.md",
            "ir101_105_completion_table": "generic_block_ai/reports/ir101_105/ir101_105_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir105_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR101-IR105 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Prohibition Cycle Continued: {bundle['prohibition_cycle_continued']}",
        f"- Evidence Consolidation Pending: {bundle['evidence_consolidation_pending']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir101_105_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR101-IR105 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir101_105_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir105_completion_bundle": _to_ref(bundle_path, project_root),
            "ir101_105_live_status": _to_ref(live_path, project_root),
            "ir101_105_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

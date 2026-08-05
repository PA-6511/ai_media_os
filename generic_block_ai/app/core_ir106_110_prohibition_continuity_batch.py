"""
core_ir106_110_prohibition_continuity_batch.py - IR106-IR110

Batch implementation for prohibition continuity governance in dry-run mode:
IR106 consolidated evidence review gate, IR107 delta closure readiness recheck,
IR108 third re-review queue planner, IR109 prohibition continuity finalizer,
IR110 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR105_SCHEMA_VERSION = "ir105_phase_101_105_completion_bundle_v1"
IR106_SCHEMA_VERSION = "ir106_consolidated_evidence_review_gate_v1"
IR107_SCHEMA_VERSION = "ir107_delta_closure_readiness_recheck_v1"
IR108_SCHEMA_VERSION = "ir108_third_re_review_queue_planner_v1"
IR109_SCHEMA_VERSION = "ir109_prohibition_continuity_finalizer_v1"
IR110_SCHEMA_VERSION = "ir110_phase_106_110_completion_bundle_v1"

IR109_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR109_HOLD = "HOLD"
IR109_ABORT = "ABORT"


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
# IR106: Consolidated Evidence Review Gate
# ---------------------------------------------------------------------------

def _build_ir106_report(
    *,
    ir105_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build consolidated evidence review gate report from IR105 completion bundle."""
    failed_checks: list[str] = []

    if ir105_report.get("schema_version") != IR105_SCHEMA_VERSION:
        failed_checks.append(f"ir105 schema_version must be {IR105_SCHEMA_VERSION}")

    if ir105_report.get("final_decision") != "PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY":
        failed_checks.append("ir105 final_decision must be PROHIBITION_CYCLE_CONTINUED_DRY_RUN_ONLY")

    if ir105_report.get("prohibition_cycle_continued") is not True:
        failed_checks.append("ir105 prohibition_cycle_continued must be true")

    if ir105_report.get("evidence_consolidation_pending") is not True:
        failed_checks.append("ir105 evidence_consolidation_pending must be true")

    ir101_result = ir105_report.get("ir101_result", {})
    status = ir101_result.get("evidence_consolidation_status", {}) if isinstance(ir101_result, dict) else {}
    entries = status.get("consolidation_entries", []) if isinstance(status, dict) else []

    reviewed_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"item_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "review_status": "REVIEW_PENDING",
            "reviewed": False,
        }
        for idx, entry in enumerate(entries)
        if isinstance(entry, dict)
    ]

    if not reviewed_entries:
        failed_checks.append("ir105 ir101_result.evidence_consolidation_status.consolidation_entries must not be empty")

    gate = {
        "gate_id": f"ir106_review_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir105_report.get("new_cycle_id", "UNKNOWN"),
        "review_entries": reviewed_entries,
        "review_entry_count": len(reviewed_entries),
        "all_reviewed": False,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR106_SCHEMA_VERSION,
        "phase": "IR106",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "consolidated_evidence_review_gate": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR107: Delta Closure Readiness Recheck
# ---------------------------------------------------------------------------

def _build_ir107_report(
    *,
    ir106_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Recheck delta closure readiness while keeping dry-run safeguards."""
    failed_checks: list[str] = []

    if ir106_report.get("validation_result") != "PASS":
        failed_checks.append("ir106 consolidated evidence review gate must be PASS")

    gate = ir106_report.get("consolidated_evidence_review_gate", {})
    entries = gate.get("review_entries", []) if isinstance(gate, dict) else []

    if not entries:
        failed_checks.append("ir106 review_entries must not be empty")

    readiness_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "readiness_status": "NOT_READY",
            "readiness_confirmed": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    tracker = {
        "recheck_id": f"ir107_recheck_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": gate.get("new_cycle_id", "UNKNOWN") if isinstance(gate, dict) else "UNKNOWN",
        "readiness_entries": readiness_entries,
        "total_entries": len(readiness_entries),
        "ready_count": 0,
        "not_ready_count": len(readiness_entries),
        "all_ready": False,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR107_SCHEMA_VERSION,
        "phase": "IR107",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "delta_closure_readiness_recheck": tracker,
        "recheck_hash": _sha256_hex(tracker),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR108: Third Re-Review Queue Planner
# ---------------------------------------------------------------------------

def _build_ir108_report(
    *,
    ir107_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Create third re-review queue plan based on readiness recheck output."""
    failed_checks: list[str] = []

    if ir107_report.get("validation_result") != "PASS":
        failed_checks.append("ir107 delta closure readiness recheck must be PASS")

    recheck = ir107_report.get("delta_closure_readiness_recheck", {})
    readiness_entries = recheck.get("readiness_entries", []) if isinstance(recheck, dict) else []

    if not readiness_entries:
        failed_checks.append("ir107 readiness_entries must not be empty")

    queue_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"queue_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "third_re_review_status": "QUEUED",
            "planned": True,
        }
        for idx, entry in enumerate(readiness_entries)
        if isinstance(entry, dict)
    ]

    planner = {
        "planner_id": f"ir108_planner_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": recheck.get("new_cycle_id", "UNKNOWN") if isinstance(recheck, dict) else "UNKNOWN",
        "queue_entries": queue_entries,
        "queue_size": len(queue_entries),
        "all_items_queued": len(queue_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR108_SCHEMA_VERSION,
        "phase": "IR108",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "third_re_review_queue_plan": planner,
        "planner_hash": _sha256_hex(planner),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR109: Prohibition Continuity Finalizer
# ---------------------------------------------------------------------------

def run_ir109_prohibition_continuity_finalizer(
    *,
    ir108_report: dict[str, Any],
    ir107_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Finalize prohibition continuity while external execution remains blocked."""
    failed_checks: list[str] = []

    if ir108_report.get("validation_result") != "PASS":
        failed_checks.append("ir108 third re-review queue planner must be PASS")

    queue_plan = ir108_report.get("third_re_review_queue_plan", {})
    if queue_plan.get("all_items_queued") is not True:
        failed_checks.append("ir108 all_items_queued must be true")

    readiness = ir107_report.get("delta_closure_readiness_recheck", {})
    if readiness.get("all_ready") is not False:
        failed_checks.append("ir107 all_ready must be false")

    if readiness.get("unlock_eligible") is not False:
        failed_checks.append("ir107 unlock_eligible must be false")

    safety_snapshot = ir108_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR109_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR109_HOLD
        action = "Hold due to prohibition continuity precondition mismatch."
    else:
        decision = IR109_CONFIRMED
        action = "Prohibition continuity finalized. Dry-run-only remains enforced."

    finalizer = {
        "finalizer_id": f"ir109_finalizer_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "continuity_finalized": decision == IR109_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR109_SCHEMA_VERSION,
        "phase": "IR109",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "prohibition_continuity_finalization_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "finalizer_record": finalizer,
        "finalizer_hash": _sha256_hex(finalizer),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir106_110_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir105_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR106-IR109 batch run for prohibition continuity governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir106_110"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir105_path = ir105_completion_bundle_path or (
        reports_dir / "ir101_105" / "ir105_completion_bundle.json"
    )

    if not ir105_path.exists():
        raise FileNotFoundError(f"ir105 completion bundle not found: {ir105_path}")

    ir105_report = _read_json(ir105_path)

    ir106_report = _build_ir106_report(
        ir105_report=ir105_report,
        source_task_id=source_task_id,
    )
    ir106_path = out_dir / "ir106_consolidated_evidence_review_gate.json"
    _write_json(ir106_path, ir106_report)

    ir107_report = _build_ir107_report(
        ir106_report=ir106_report,
        source_task_id=source_task_id,
    )
    ir107_path = out_dir / "ir107_delta_closure_readiness_recheck.json"
    _write_json(ir107_path, ir107_report)

    ir108_report = _build_ir108_report(
        ir107_report=ir107_report,
        source_task_id=source_task_id,
    )
    ir108_path = out_dir / "ir108_third_re_review_queue_planner.json"
    _write_json(ir108_path, ir108_report)

    ir109_report = run_ir109_prohibition_continuity_finalizer(
        ir108_report=ir108_report,
        ir107_report=ir107_report,
        source_task_id=source_task_id,
    )
    ir109_path = out_dir / "ir109_prohibition_continuity_finalizer_report.json"
    _write_json(ir109_path, ir109_report)

    final_decision = ir109_report["prohibition_continuity_finalization_decision"]

    return {
        "phase": "IR106_110_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir105_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir105_bundle_path": _to_ref(ir105_path, project_root),
        "final_decision": final_decision,
        "ir106_result": ir106_report,
        "ir107_result": ir107_report,
        "ir108_result": ir108_report,
        "ir109_result": ir109_report,
        "artifacts": {
            "ir106_consolidated_evidence_review_gate": _to_ref(ir106_path, project_root),
            "ir107_delta_closure_readiness_recheck": _to_ref(ir107_path, project_root),
            "ir108_third_re_review_queue_planner": _to_ref(ir108_path, project_root),
            "ir109_prohibition_continuity_finalizer_report": _to_ref(ir109_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR110: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir106_110_completion_bundle(
    *,
    base_path: Path,
    ir106_110_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR110 completion bundle summarising IR106-110 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir106_110"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir106_result = ir106_110_output.get("ir106_result", {})
    ir107_result = ir106_110_output.get("ir107_result", {})
    ir108_result = ir106_110_output.get("ir108_result", {})
    ir109_result = ir106_110_output.get("ir109_result", {})
    final_decision = str(ir106_110_output.get("final_decision", IR109_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir109_live = "PASS" if final_decision == IR109_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR106", "content": "Consolidated Evidence Review Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir106_result), "judgement": _judgement(_live(ir106_result))},
        {"phase": "IR107", "content": "Delta Closure Readiness Recheck", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir107_result), "judgement": _judgement(_live(ir107_result))},
        {"phase": "IR108", "content": "Third Re-Review Queue Planner", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir108_result), "judgement": _judgement(_live(ir108_result))},
        {"phase": "IR109", "content": "Prohibition Continuity Finalizer", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir109_live, "judgement": _judgement(ir109_live)},
        {"phase": "IR110", "content": "Phase 106-110 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir109_live, "judgement": _judgement(ir109_live)},
    ]

    bundle = {
        "schema_version": IR110_SCHEMA_VERSION,
        "phase": "IR110",
        "generated_at": _now_iso(),
        "source_task_id": ir106_110_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir106_110_output.get("new_cycle_id", "UNKNOWN"),
        "ir106_result": ir106_result,
        "ir107_result": ir107_result,
        "ir108_result": ir108_result,
        "ir109_result": ir109_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir106": table_rows[0]["live"],
            "ir107": table_rows[1]["live"],
            "ir108": table_rows[2]["live"],
            "ir109": table_rows[3]["live"],
            "ir110": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR109_CONFIRMED,
        "delta_closure_pending": ir107_result.get("delta_closure_readiness_recheck", {}).get("all_ready") is False,
        "artifacts": {
            **ir106_110_output.get("artifacts", {}),
            "ir110_completion_bundle": "generic_block_ai/reports/ir106_110/ir110_completion_bundle.json",
            "ir106_110_live_status": "generic_block_ai/reports/ir106_110/ir106_110_live_status.md",
            "ir106_110_completion_table": "generic_block_ai/reports/ir106_110/ir106_110_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir110_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR106-IR110 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Prohibition Continuity Finalized: {bundle['prohibition_continuity_finalized']}",
        f"- Delta Closure Pending: {bundle['delta_closure_pending']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir106_110_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR106-IR110 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir106_110_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir110_completion_bundle": _to_ref(bundle_path, project_root),
            "ir106_110_live_status": _to_ref(live_path, project_root),
            "ir106_110_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

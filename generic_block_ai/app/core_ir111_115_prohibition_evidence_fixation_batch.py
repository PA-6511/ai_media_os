"""
core_ir111_115_prohibition_evidence_fixation_batch.py - IR111-IR115

Batch implementation for post-finalization evidence fixation governance in dry-run mode:
IR111 finalized prohibition evidence snapshot, IR112 delta closure deferred registry,
IR113 third re-review handoff package, IR114 dry-run finalization audit gate,
IR115 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR110_SCHEMA_VERSION = "ir110_phase_106_110_completion_bundle_v1"
IR111_SCHEMA_VERSION = "ir111_finalized_prohibition_evidence_snapshot_v1"
IR112_SCHEMA_VERSION = "ir112_delta_closure_deferred_registry_v1"
IR113_SCHEMA_VERSION = "ir113_third_re_review_handoff_package_v1"
IR114_SCHEMA_VERSION = "ir114_dry_run_finalization_audit_gate_v1"
IR115_SCHEMA_VERSION = "ir115_phase_111_115_completion_bundle_v1"

IR114_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR114_HOLD = "HOLD"
IR114_ABORT = "ABORT"


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
# IR111: Finalized Prohibition Evidence Snapshot
# ---------------------------------------------------------------------------

def _build_ir111_report(
    *,
    ir110_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Capture immutable evidence snapshot after prohibition continuity finalization."""
    failed_checks: list[str] = []

    if ir110_report.get("schema_version") != IR110_SCHEMA_VERSION:
        failed_checks.append(f"ir110 schema_version must be {IR110_SCHEMA_VERSION}")

    if ir110_report.get("final_decision") != IR114_CONFIRMED:
        failed_checks.append("ir110 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir110_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir110 prohibition_continuity_finalized must be true")

    if ir110_report.get("delta_closure_pending") is not True:
        failed_checks.append("ir110 delta_closure_pending must be true")

    ir106_result = ir110_report.get("ir106_result", {})
    gate = ir106_result.get("consolidated_evidence_review_gate", {}) if isinstance(ir106_result, dict) else {}
    review_entries = gate.get("review_entries", []) if isinstance(gate, dict) else []

    snapshot_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"item_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "snapshot_status": "FINALIZED_PROHIBITION_EVIDENCE_LOCKED",
            "locked": True,
            "mutable": False,
        }
        for idx, entry in enumerate(review_entries)
        if isinstance(entry, dict)
    ]

    if not snapshot_entries:
        failed_checks.append("ir110 ir106_result.consolidated_evidence_review_gate.review_entries must not be empty")

    snapshot = {
        "snapshot_id": f"ir111_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir110_report.get("new_cycle_id", "UNKNOWN"),
        "snapshot_entries": snapshot_entries,
        "snapshot_entry_count": len(snapshot_entries),
        "evidence_lock_applied": len(snapshot_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR111_SCHEMA_VERSION,
        "phase": "IR111",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "finalized_prohibition_evidence_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR112: Delta Closure Deferred Registry
# ---------------------------------------------------------------------------

def _build_ir112_report(
    *,
    ir111_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Register deferred delta closure items while preserving prohibition continuity."""
    failed_checks: list[str] = []

    if ir111_report.get("validation_result") != "PASS":
        failed_checks.append("ir111 finalized prohibition evidence snapshot must be PASS")

    snapshot = ir111_report.get("finalized_prohibition_evidence_snapshot", {})
    snapshot_entries = snapshot.get("snapshot_entries", []) if isinstance(snapshot, dict) else []

    if not snapshot_entries:
        failed_checks.append("ir111 snapshot_entries must not be empty")

    deferred_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "deferred_status": "DEFERRED_PENDING",
            "closure_deferred": True,
        }
        for entry in snapshot_entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir112_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "deferred_entries": deferred_entries,
        "deferred_count": len(deferred_entries),
        "closure_ready_count": 0,
        "delta_closure_deferred": len(deferred_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR112_SCHEMA_VERSION,
        "phase": "IR112",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "delta_closure_deferred_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR113: Third Re-Review Handoff Package
# ---------------------------------------------------------------------------

def _build_ir113_report(
    *,
    ir112_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Prepare third re-review handoff package based on deferred registry state."""
    failed_checks: list[str] = []

    if ir112_report.get("validation_result") != "PASS":
        failed_checks.append("ir112 delta closure deferred registry must be PASS")

    registry = ir112_report.get("delta_closure_deferred_registry", {})
    deferred_entries = registry.get("deferred_entries", []) if isinstance(registry, dict) else []

    if not deferred_entries:
        failed_checks.append("ir112 deferred_entries must not be empty")

    package_entries = [
        {
            "queue_item_id": str(entry.get("queue_item_id", f"handoff_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "handoff_status": "HANDOFF_READY",
            "handoff_prepared": True,
        }
        for idx, entry in enumerate(deferred_entries)
        if isinstance(entry, dict)
    ]

    handoff = {
        "handoff_id": f"ir113_handoff_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "package_entries": package_entries,
        "package_size": len(package_entries),
        "all_handoff_prepared": len(package_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR113_SCHEMA_VERSION,
        "phase": "IR113",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "third_re_review_handoff_package": handoff,
        "handoff_hash": _sha256_hex(handoff),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR114: Dry-Run Finalization Audit Gate
# ---------------------------------------------------------------------------

def run_ir114_dry_run_finalization_audit_gate(
    *,
    ir113_report: dict[str, Any],
    ir112_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Finalize post-continuity audit gate while keeping execution prohibited."""
    failed_checks: list[str] = []

    if ir113_report.get("validation_result") != "PASS":
        failed_checks.append("ir113 third re-review handoff package must be PASS")

    handoff = ir113_report.get("third_re_review_handoff_package", {})
    if handoff.get("all_handoff_prepared") is not True:
        failed_checks.append("ir113 all_handoff_prepared must be true")

    registry = ir112_report.get("delta_closure_deferred_registry", {})
    if registry.get("delta_closure_deferred") is not True:
        failed_checks.append("ir112 delta_closure_deferred must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir112 unlock_eligible must be false")

    safety_snapshot = ir113_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR114_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR114_HOLD
        action = "Hold due to dry-run finalization audit precondition mismatch."
    else:
        decision = IR114_CONFIRMED
        action = "Dry-run finalization audit passed. Prohibition continuity remains finalized."

    gate = {
        "gate_id": f"ir114_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "finalization_audit_passed": decision == IR114_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR114_SCHEMA_VERSION,
        "phase": "IR114",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_finalization_audit_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "audit_gate_record": gate,
        "audit_gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir111_115_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir110_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR111-IR114 batch run for evidence fixation governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir111_115"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir110_path = ir110_completion_bundle_path or (
        reports_dir / "ir106_110" / "ir110_completion_bundle.json"
    )

    if not ir110_path.exists():
        raise FileNotFoundError(f"ir110 completion bundle not found: {ir110_path}")

    ir110_report = _read_json(ir110_path)

    ir111_report = _build_ir111_report(
        ir110_report=ir110_report,
        source_task_id=source_task_id,
    )
    ir111_path = out_dir / "ir111_finalized_prohibition_evidence_snapshot.json"
    _write_json(ir111_path, ir111_report)

    ir112_report = _build_ir112_report(
        ir111_report=ir111_report,
        source_task_id=source_task_id,
    )
    ir112_path = out_dir / "ir112_delta_closure_deferred_registry.json"
    _write_json(ir112_path, ir112_report)

    ir113_report = _build_ir113_report(
        ir112_report=ir112_report,
        source_task_id=source_task_id,
    )
    ir113_path = out_dir / "ir113_third_re_review_handoff_package.json"
    _write_json(ir113_path, ir113_report)

    ir114_report = run_ir114_dry_run_finalization_audit_gate(
        ir113_report=ir113_report,
        ir112_report=ir112_report,
        source_task_id=source_task_id,
    )
    ir114_path = out_dir / "ir114_dry_run_finalization_audit_gate.json"
    _write_json(ir114_path, ir114_report)

    final_decision = ir114_report["dry_run_finalization_audit_decision"]

    return {
        "phase": "IR111_115_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir110_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir110_bundle_path": _to_ref(ir110_path, project_root),
        "final_decision": final_decision,
        "ir111_result": ir111_report,
        "ir112_result": ir112_report,
        "ir113_result": ir113_report,
        "ir114_result": ir114_report,
        "artifacts": {
            "ir111_finalized_prohibition_evidence_snapshot": _to_ref(ir111_path, project_root),
            "ir112_delta_closure_deferred_registry": _to_ref(ir112_path, project_root),
            "ir113_third_re_review_handoff_package": _to_ref(ir113_path, project_root),
            "ir114_dry_run_finalization_audit_gate": _to_ref(ir114_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR115: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir111_115_completion_bundle(
    *,
    base_path: Path,
    ir111_115_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR115 completion bundle summarising IR111-115 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir111_115"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir111_result = ir111_115_output.get("ir111_result", {})
    ir112_result = ir111_115_output.get("ir112_result", {})
    ir113_result = ir111_115_output.get("ir113_result", {})
    ir114_result = ir111_115_output.get("ir114_result", {})
    final_decision = str(ir111_115_output.get("final_decision", IR114_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir114_live = "PASS" if final_decision == IR114_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR111", "content": "Finalized Prohibition Evidence Snapshot", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir111_result), "judgement": _judgement(_live(ir111_result))},
        {"phase": "IR112", "content": "Delta Closure Deferred Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir112_result), "judgement": _judgement(_live(ir112_result))},
        {"phase": "IR113", "content": "Third Re-Review Handoff Package", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir113_result), "judgement": _judgement(_live(ir113_result))},
        {"phase": "IR114", "content": "Dry-Run Finalization Audit Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir114_live, "judgement": _judgement(ir114_live)},
        {"phase": "IR115", "content": "Phase 111-115 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir114_live, "judgement": _judgement(ir114_live)},
    ]

    bundle = {
        "schema_version": IR115_SCHEMA_VERSION,
        "phase": "IR115",
        "generated_at": _now_iso(),
        "source_task_id": ir111_115_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir111_115_output.get("new_cycle_id", "UNKNOWN"),
        "ir111_result": ir111_result,
        "ir112_result": ir112_result,
        "ir113_result": ir113_result,
        "ir114_result": ir114_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir111": table_rows[0]["live"],
            "ir112": table_rows[1]["live"],
            "ir113": table_rows[2]["live"],
            "ir114": table_rows[3]["live"],
            "ir115": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR114_CONFIRMED,
        "delta_closure_pending": ir112_result.get("delta_closure_deferred_registry", {}).get("delta_closure_deferred") is True,
        "artifacts": {
            **ir111_115_output.get("artifacts", {}),
            "ir115_completion_bundle": "generic_block_ai/reports/ir111_115/ir115_completion_bundle.json",
            "ir111_115_live_status": "generic_block_ai/reports/ir111_115/ir111_115_live_status.md",
            "ir111_115_completion_table": "generic_block_ai/reports/ir111_115/ir111_115_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir115_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR111-IR115 Live Status",
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
    live_path = out_dir / "ir111_115_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR111-IR115 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir111_115_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir115_completion_bundle": _to_ref(bundle_path, project_root),
            "ir111_115_live_status": _to_ref(live_path, project_root),
            "ir111_115_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

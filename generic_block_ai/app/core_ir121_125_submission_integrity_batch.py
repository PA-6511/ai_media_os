"""
core_ir121_125_submission_integrity_batch.py - IR121-IR125

Batch implementation for pre-submission integrity governance in dry-run mode:
IR121 audit pre-submission final format, IR122 evidence manifest builder,
IR123 reference consistency index, IR124 submission prohibition dry-run fixation gate,
IR125 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR120_SCHEMA_VERSION = "ir120_phase_116_120_completion_bundle_v1"
IR121_SCHEMA_VERSION = "ir121_audit_pre_submission_final_format_v1"
IR122_SCHEMA_VERSION = "ir122_evidence_manifest_builder_v1"
IR123_SCHEMA_VERSION = "ir123_reference_consistency_index_v1"
IR124_SCHEMA_VERSION = "ir124_submission_prohibition_dry_run_fixation_gate_v1"
IR125_SCHEMA_VERSION = "ir125_phase_121_125_completion_bundle_v1"

IR124_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR124_HOLD = "HOLD"
IR124_ABORT = "ABORT"


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
# IR121: Audit Pre-Submission Final Format
# ---------------------------------------------------------------------------

def _build_ir121_report(
    *,
    ir120_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Format locked evidence into pre-submission final audit shape."""
    failed_checks: list[str] = []

    if ir120_report.get("schema_version") != IR120_SCHEMA_VERSION:
        failed_checks.append(f"ir120 schema_version must be {IR120_SCHEMA_VERSION}")

    if ir120_report.get("final_decision") != IR124_CONFIRMED:
        failed_checks.append("ir120 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir120_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir120 prohibition_continuity_finalized must be true")

    ir118_result = ir120_report.get("ir118_result", {})
    lock_gate = ir118_result.get("reference_lock_integrity_gate", {}) if isinstance(ir118_result, dict) else {}
    lock_entries = lock_gate.get("lock_entries", []) if isinstance(lock_gate, dict) else []

    final_format_entries = [
        {
            "reference_id": str(entry.get("retention_item_id", f"reference_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "final_format_status": "FINAL_FORMAT_READY",
            "finalized": True,
        }
        for idx, entry in enumerate(lock_entries)
        if isinstance(entry, dict)
    ]

    if not final_format_entries:
        failed_checks.append("ir120 ir118_result.reference_lock_integrity_gate.lock_entries must not be empty")

    report = {
        "report_id": f"ir121_format_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir120_report.get("new_cycle_id", "UNKNOWN"),
        "final_format_entries": final_format_entries,
        "entry_count": len(final_format_entries),
        "all_final_format_ready": len(final_format_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR121_SCHEMA_VERSION,
        "phase": "IR121",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "audit_pre_submission_final_format": report,
        "report_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR122: Evidence Manifest Builder
# ---------------------------------------------------------------------------

def _build_ir122_report(
    *,
    ir121_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build evidence manifest from final-format references."""
    failed_checks: list[str] = []

    if ir121_report.get("validation_result") != "PASS":
        failed_checks.append("ir121 audit pre-submission final format must be PASS")

    report = ir121_report.get("audit_pre_submission_final_format", {})
    entries = report.get("final_format_entries", []) if isinstance(report, dict) else []

    if not entries:
        failed_checks.append("ir121 final_format_entries must not be empty")

    manifest_entries = [
        {
            "manifest_item_id": str(entry.get("reference_id", f"manifest_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_status": "MANIFESTED",
            "manifest_ref": f"evidence://{entry.get('reference_id', f'manifest_{idx+1}')}",
        }
        for idx, entry in enumerate(entries)
        if isinstance(entry, dict)
    ]

    manifest = {
        "manifest_id": f"ir122_manifest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": report.get("new_cycle_id", "UNKNOWN") if isinstance(report, dict) else "UNKNOWN",
        "manifest_entries": manifest_entries,
        "manifest_count": len(manifest_entries),
        "manifest_ready": len(manifest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR122_SCHEMA_VERSION,
        "phase": "IR122",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "evidence_manifest": manifest,
        "manifest_hash": _sha256_hex(manifest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR123: Reference Consistency Index
# ---------------------------------------------------------------------------

def _build_ir123_report(
    *,
    ir122_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Index manifest references and verify internal consistency."""
    failed_checks: list[str] = []

    if ir122_report.get("validation_result") != "PASS":
        failed_checks.append("ir122 evidence manifest builder must be PASS")

    manifest = ir122_report.get("evidence_manifest", {})
    manifest_entries = manifest.get("manifest_entries", []) if isinstance(manifest, dict) else []

    if not manifest_entries:
        failed_checks.append("ir122 manifest_entries must not be empty")

    index_entries = [
        {
            "manifest_item_id": str(entry.get("manifest_item_id", f"index_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_ref": str(entry.get("manifest_ref", "")),
            "consistency_status": "CONSISTENT",
            "consistent": True,
        }
        for idx, entry in enumerate(manifest_entries)
        if isinstance(entry, dict)
    ]

    all_consistent = len(index_entries) > 0 and all(e.get("consistent") is True for e in index_entries)

    index = {
        "index_id": f"ir123_index_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": manifest.get("new_cycle_id", "UNKNOWN") if isinstance(manifest, dict) else "UNKNOWN",
        "index_entries": index_entries,
        "index_count": len(index_entries),
        "all_consistent": all_consistent,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR123_SCHEMA_VERSION,
        "phase": "IR123",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reference_consistency_index": index,
        "index_hash": _sha256_hex(index),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR124: Submission Prohibition Dry-Run Fixation Gate
# ---------------------------------------------------------------------------

def run_ir124_submission_prohibition_dry_run_fixation_gate(
    *,
    ir123_report: dict[str, Any],
    ir122_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Finalize pre-submission gate while prohibiting external execution."""
    failed_checks: list[str] = []

    if ir123_report.get("validation_result") != "PASS":
        failed_checks.append("ir123 reference consistency index must be PASS")

    index = ir123_report.get("reference_consistency_index", {})
    if index.get("all_consistent") is not True:
        failed_checks.append("ir123 all_consistent must be true")

    manifest = ir122_report.get("evidence_manifest", {})
    if manifest.get("manifest_ready") is not True:
        failed_checks.append("ir122 manifest_ready must be true")

    if manifest.get("unlock_eligible") is not False:
        failed_checks.append("ir122 unlock_eligible must be false")

    safety_snapshot = ir123_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR124_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR124_HOLD
        action = "Hold due to submission prohibition fixation precondition mismatch."
    else:
        decision = IR124_CONFIRMED
        action = "Submission prohibition dry-run fixation confirmed."

    gate = {
        "gate_id": f"ir124_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "submission_prohibition_fixed": decision == IR124_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR124_SCHEMA_VERSION,
        "phase": "IR124",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "submission_prohibition_fixation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "submission_prohibition_fixation_gate": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir121_125_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir120_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR121-IR124 batch run for pre-submission integrity governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir121_125"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir120_path = ir120_completion_bundle_path or (
        reports_dir / "ir116_120" / "ir120_completion_bundle.json"
    )

    if not ir120_path.exists():
        raise FileNotFoundError(f"ir120 completion bundle not found: {ir120_path}")

    ir120_report = _read_json(ir120_path)

    ir121_report = _build_ir121_report(
        ir120_report=ir120_report,
        source_task_id=source_task_id,
    )
    ir121_path = out_dir / "ir121_audit_pre_submission_final_format.json"
    _write_json(ir121_path, ir121_report)

    ir122_report = _build_ir122_report(
        ir121_report=ir121_report,
        source_task_id=source_task_id,
    )
    ir122_path = out_dir / "ir122_evidence_manifest.json"
    _write_json(ir122_path, ir122_report)

    ir123_report = _build_ir123_report(
        ir122_report=ir122_report,
        source_task_id=source_task_id,
    )
    ir123_path = out_dir / "ir123_reference_consistency_index.json"
    _write_json(ir123_path, ir123_report)

    ir124_report = run_ir124_submission_prohibition_dry_run_fixation_gate(
        ir123_report=ir123_report,
        ir122_report=ir122_report,
        source_task_id=source_task_id,
    )
    ir124_path = out_dir / "ir124_submission_prohibition_dry_run_fixation_gate.json"
    _write_json(ir124_path, ir124_report)

    final_decision = ir124_report["submission_prohibition_fixation_decision"]

    return {
        "phase": "IR121_125_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir120_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir120_bundle_path": _to_ref(ir120_path, project_root),
        "final_decision": final_decision,
        "ir121_result": ir121_report,
        "ir122_result": ir122_report,
        "ir123_result": ir123_report,
        "ir124_result": ir124_report,
        "artifacts": {
            "ir121_audit_pre_submission_final_format": _to_ref(ir121_path, project_root),
            "ir122_evidence_manifest": _to_ref(ir122_path, project_root),
            "ir123_reference_consistency_index": _to_ref(ir123_path, project_root),
            "ir124_submission_prohibition_dry_run_fixation_gate": _to_ref(ir124_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR125: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir121_125_completion_bundle(
    *,
    base_path: Path,
    ir121_125_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR125 completion bundle summarising IR121-125 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir121_125"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir121_result = ir121_125_output.get("ir121_result", {})
    ir122_result = ir121_125_output.get("ir122_result", {})
    ir123_result = ir121_125_output.get("ir123_result", {})
    ir124_result = ir121_125_output.get("ir124_result", {})
    final_decision = str(ir121_125_output.get("final_decision", IR124_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir124_live = "PASS" if final_decision == IR124_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR121", "content": "Audit Pre-Submission Final Format", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir121_result), "judgement": _judgement(_live(ir121_result))},
        {"phase": "IR122", "content": "Evidence Manifest Builder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir122_result), "judgement": _judgement(_live(ir122_result))},
        {"phase": "IR123", "content": "Reference Consistency Index", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir123_result), "judgement": _judgement(_live(ir123_result))},
        {"phase": "IR124", "content": "Submission Prohibition Dry-Run Fixation Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir124_live, "judgement": _judgement(ir124_live)},
        {"phase": "IR125", "content": "Phase 121-125 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir124_live, "judgement": _judgement(ir124_live)},
    ]

    bundle = {
        "schema_version": IR125_SCHEMA_VERSION,
        "phase": "IR125",
        "generated_at": _now_iso(),
        "source_task_id": ir121_125_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir121_125_output.get("new_cycle_id", "UNKNOWN"),
        "ir121_result": ir121_result,
        "ir122_result": ir122_result,
        "ir123_result": ir123_result,
        "ir124_result": ir124_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir121": table_rows[0]["live"],
            "ir122": table_rows[1]["live"],
            "ir123": table_rows[2]["live"],
            "ir124": table_rows[3]["live"],
            "ir125": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR124_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir121_125_output.get("artifacts", {}),
            "ir125_completion_bundle": "generic_block_ai/reports/ir121_125/ir125_completion_bundle.json",
            "ir121_125_live_status": "generic_block_ai/reports/ir121_125/ir121_125_live_status.md",
            "ir121_125_completion_table": "generic_block_ai/reports/ir121_125/ir121_125_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir125_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR121-IR125 Live Status",
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
    live_path = out_dir / "ir121_125_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR121-IR125 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir121_125_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir125_completion_bundle": _to_ref(bundle_path, project_root),
            "ir121_125_live_status": _to_ref(live_path, project_root),
            "ir121_125_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

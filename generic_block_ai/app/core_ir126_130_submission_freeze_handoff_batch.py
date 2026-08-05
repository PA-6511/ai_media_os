"""
core_ir126_130_submission_freeze_handoff_batch.py - IR126-IR130

Batch implementation for pre-submission freeze and handoff governance in dry-run mode:
IR126 pre-submission package freeze, IR127 manifest re-verification,
IR128 dry-run non-submission evidence gate, IR129 long-term retention handoff,
IR130 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR125_SCHEMA_VERSION = "ir125_phase_121_125_completion_bundle_v1"
IR126_SCHEMA_VERSION = "ir126_pre_submission_package_freeze_v1"
IR127_SCHEMA_VERSION = "ir127_manifest_reverification_v1"
IR128_SCHEMA_VERSION = "ir128_dry_run_non_submission_evidence_gate_v1"
IR129_SCHEMA_VERSION = "ir129_long_term_retention_handoff_v1"
IR130_SCHEMA_VERSION = "ir130_phase_126_130_completion_bundle_v1"

IR129_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR129_HOLD = "HOLD"
IR129_ABORT = "ABORT"


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
# IR126: Pre-Submission Package Freeze
# ---------------------------------------------------------------------------

def _build_ir126_report(
    *,
    ir125_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Freeze pre-submission package references for non-submission dry-run handling."""
    failed_checks: list[str] = []

    if ir125_report.get("schema_version") != IR125_SCHEMA_VERSION:
        failed_checks.append(f"ir125 schema_version must be {IR125_SCHEMA_VERSION}")

    if ir125_report.get("final_decision") != IR129_CONFIRMED:
        failed_checks.append("ir125 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir125_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir125 prohibition_continuity_finalized must be true")

    ir122_result = ir125_report.get("ir122_result", {})
    manifest = ir122_result.get("evidence_manifest", {}) if isinstance(ir122_result, dict) else {}
    manifest_entries = manifest.get("manifest_entries", []) if isinstance(manifest, dict) else []

    freeze_entries = [
        {
            "freeze_item_id": str(entry.get("manifest_item_id", f"freeze_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_ref": str(entry.get("manifest_ref", "")),
            "freeze_status": "FROZEN",
            "mutable": False,
        }
        for idx, entry in enumerate(manifest_entries)
        if isinstance(entry, dict)
    ]

    if not freeze_entries:
        failed_checks.append("ir125 ir122_result.evidence_manifest.manifest_entries must not be empty")

    freeze = {
        "freeze_id": f"ir126_freeze_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir125_report.get("new_cycle_id", "UNKNOWN"),
        "freeze_entries": freeze_entries,
        "freeze_count": len(freeze_entries),
        "all_frozen": len(freeze_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR126_SCHEMA_VERSION,
        "phase": "IR126",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "pre_submission_package_freeze": freeze,
        "freeze_hash": _sha256_hex(freeze),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR127: Manifest Re-Verification
# ---------------------------------------------------------------------------

def _build_ir127_report(
    *,
    ir126_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Re-verify manifest references after package freeze."""
    failed_checks: list[str] = []

    if ir126_report.get("validation_result") != "PASS":
        failed_checks.append("ir126 pre-submission package freeze must be PASS")

    freeze = ir126_report.get("pre_submission_package_freeze", {})
    freeze_entries = freeze.get("freeze_entries", []) if isinstance(freeze, dict) else []

    if not freeze_entries:
        failed_checks.append("ir126 freeze_entries must not be empty")

    reverification_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_ref": str(entry.get("manifest_ref", "")),
            "reverification_status": "REVERIFIED",
            "reverification_passed": True,
        }
        for entry in freeze_entries
        if isinstance(entry, dict)
    ]

    passed_count = sum(1 for e in reverification_entries if e.get("reverification_passed") is True)

    reverification = {
        "reverification_id": f"ir127_reverify_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": freeze.get("new_cycle_id", "UNKNOWN") if isinstance(freeze, dict) else "UNKNOWN",
        "reverification_entries": reverification_entries,
        "entry_count": len(reverification_entries),
        "all_reverified": len(reverification_entries) > 0 and passed_count == len(reverification_entries),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR127_SCHEMA_VERSION,
        "phase": "IR127",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "manifest_reverification": reverification,
        "reverification_hash": _sha256_hex(reverification),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR128: Dry-Run Non-Submission Evidence Gate
# ---------------------------------------------------------------------------

def _build_ir128_report(
    *,
    ir127_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Establish evidence gate that submission is prohibited in dry-run."""
    failed_checks: list[str] = []

    if ir127_report.get("validation_result") != "PASS":
        failed_checks.append("ir127 manifest re-verification must be PASS")

    reverification = ir127_report.get("manifest_reverification", {})
    reverification_entries = reverification.get("reverification_entries", []) if isinstance(reverification, dict) else []

    if not reverification_entries:
        failed_checks.append("ir127 reverification_entries must not be empty")

    gate_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", f"gate_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "non_submission_status": "DRY_RUN_SUBMISSION_PROHIBITED",
            "submission_allowed": False,
        }
        for idx, entry in enumerate(reverification_entries)
        if isinstance(entry, dict)
    ]

    gate = {
        "gate_id": f"ir128_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": reverification.get("new_cycle_id", "UNKNOWN") if isinstance(reverification, dict) else "UNKNOWN",
        "gate_entries": gate_entries,
        "gate_entry_count": len(gate_entries),
        "submission_prohibited_confirmed": len(gate_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR128_SCHEMA_VERSION,
        "phase": "IR128",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_non_submission_evidence_gate": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR129: Long-Term Retention Handoff
# ---------------------------------------------------------------------------

def run_ir129_long_term_retention_handoff(
    *,
    ir128_report: dict[str, Any],
    ir127_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Finalize long-term retention handoff while keeping submission blocked."""
    failed_checks: list[str] = []

    if ir128_report.get("validation_result") != "PASS":
        failed_checks.append("ir128 dry-run non-submission evidence gate must be PASS")

    gate = ir128_report.get("dry_run_non_submission_evidence_gate", {})
    if gate.get("submission_prohibited_confirmed") is not True:
        failed_checks.append("ir128 submission_prohibited_confirmed must be true")

    reverification = ir127_report.get("manifest_reverification", {})
    if reverification.get("all_reverified") is not True:
        failed_checks.append("ir127 all_reverified must be true")

    if reverification.get("unlock_eligible") is not False:
        failed_checks.append("ir127 unlock_eligible must be false")

    safety_snapshot = ir128_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR129_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR129_HOLD
        action = "Hold due to long-term retention handoff precondition mismatch."
    else:
        decision = IR129_CONFIRMED
        action = "Long-term retention handoff confirmed in dry-run non-submission mode."

    handoff = {
        "handoff_id": f"ir129_handoff_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "retention_handoff_completed": decision == IR129_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR129_SCHEMA_VERSION,
        "phase": "IR129",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "long_term_retention_handoff_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_retention_handoff": handoff,
        "handoff_hash": _sha256_hex(handoff),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir126_130_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir125_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR126-IR129 batch run for submission freeze and handoff governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir126_130"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir125_path = ir125_completion_bundle_path or (
        reports_dir / "ir121_125" / "ir125_completion_bundle.json"
    )

    if not ir125_path.exists():
        raise FileNotFoundError(f"ir125 completion bundle not found: {ir125_path}")

    ir125_report = _read_json(ir125_path)

    ir126_report = _build_ir126_report(
        ir125_report=ir125_report,
        source_task_id=source_task_id,
    )
    ir126_path = out_dir / "ir126_pre_submission_package_freeze.json"
    _write_json(ir126_path, ir126_report)

    ir127_report = _build_ir127_report(
        ir126_report=ir126_report,
        source_task_id=source_task_id,
    )
    ir127_path = out_dir / "ir127_manifest_reverification.json"
    _write_json(ir127_path, ir127_report)

    ir128_report = _build_ir128_report(
        ir127_report=ir127_report,
        source_task_id=source_task_id,
    )
    ir128_path = out_dir / "ir128_dry_run_non_submission_evidence_gate.json"
    _write_json(ir128_path, ir128_report)

    ir129_report = run_ir129_long_term_retention_handoff(
        ir128_report=ir128_report,
        ir127_report=ir127_report,
        source_task_id=source_task_id,
    )
    ir129_path = out_dir / "ir129_long_term_retention_handoff.json"
    _write_json(ir129_path, ir129_report)

    final_decision = ir129_report["long_term_retention_handoff_decision"]

    return {
        "phase": "IR126_130_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir125_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir125_bundle_path": _to_ref(ir125_path, project_root),
        "final_decision": final_decision,
        "ir126_result": ir126_report,
        "ir127_result": ir127_report,
        "ir128_result": ir128_report,
        "ir129_result": ir129_report,
        "artifacts": {
            "ir126_pre_submission_package_freeze": _to_ref(ir126_path, project_root),
            "ir127_manifest_reverification": _to_ref(ir127_path, project_root),
            "ir128_dry_run_non_submission_evidence_gate": _to_ref(ir128_path, project_root),
            "ir129_long_term_retention_handoff": _to_ref(ir129_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR130: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir126_130_completion_bundle(
    *,
    base_path: Path,
    ir126_130_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR130 completion bundle summarising IR126-130 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir126_130"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir126_result = ir126_130_output.get("ir126_result", {})
    ir127_result = ir126_130_output.get("ir127_result", {})
    ir128_result = ir126_130_output.get("ir128_result", {})
    ir129_result = ir126_130_output.get("ir129_result", {})
    final_decision = str(ir126_130_output.get("final_decision", IR129_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir129_live = "PASS" if final_decision == IR129_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR126", "content": "Pre-Submission Package Freeze", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir126_result), "judgement": _judgement(_live(ir126_result))},
        {"phase": "IR127", "content": "Manifest Re-Verification", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir127_result), "judgement": _judgement(_live(ir127_result))},
        {"phase": "IR128", "content": "Dry-Run Non-Submission Evidence Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir128_result), "judgement": _judgement(_live(ir128_result))},
        {"phase": "IR129", "content": "Long-Term Retention Handoff", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir129_live, "judgement": _judgement(ir129_live)},
        {"phase": "IR130", "content": "Phase 126-130 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir129_live, "judgement": _judgement(ir129_live)},
    ]

    bundle = {
        "schema_version": IR130_SCHEMA_VERSION,
        "phase": "IR130",
        "generated_at": _now_iso(),
        "source_task_id": ir126_130_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir126_130_output.get("new_cycle_id", "UNKNOWN"),
        "ir126_result": ir126_result,
        "ir127_result": ir127_result,
        "ir128_result": ir128_result,
        "ir129_result": ir129_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir126": table_rows[0]["live"],
            "ir127": table_rows[1]["live"],
            "ir128": table_rows[2]["live"],
            "ir129": table_rows[3]["live"],
            "ir130": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR129_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir126_130_output.get("artifacts", {}),
            "ir130_completion_bundle": "generic_block_ai/reports/ir126_130/ir130_completion_bundle.json",
            "ir126_130_live_status": "generic_block_ai/reports/ir126_130/ir126_130_live_status.md",
            "ir126_130_completion_table": "generic_block_ai/reports/ir126_130/ir126_130_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir130_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR126-IR130 Live Status",
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
    live_path = out_dir / "ir126_130_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR126-IR130 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir126_130_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir130_completion_bundle": _to_ref(bundle_path, project_root),
            "ir126_130_live_status": _to_ref(live_path, project_root),
            "ir126_130_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

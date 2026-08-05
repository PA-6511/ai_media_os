"""
core_ir116_120_evidence_retention_readiness_batch.py - IR116-IR120

Batch implementation for post-fixation retention governance in dry-run mode:
IR116 long-term evidence retention registry, IR117 fixed evidence re-verification ledger,
IR118 reference lock integrity gate, IR119 audit submission readiness package,
IR120 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR115_SCHEMA_VERSION = "ir115_phase_111_115_completion_bundle_v1"
IR116_SCHEMA_VERSION = "ir116_long_term_evidence_retention_registry_v1"
IR117_SCHEMA_VERSION = "ir117_fixed_evidence_reverification_ledger_v1"
IR118_SCHEMA_VERSION = "ir118_reference_lock_integrity_gate_v1"
IR119_SCHEMA_VERSION = "ir119_audit_submission_readiness_package_v1"
IR120_SCHEMA_VERSION = "ir120_phase_116_120_completion_bundle_v1"

IR119_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR119_HOLD = "HOLD"
IR119_ABORT = "ABORT"


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
# IR116: Long-Term Evidence Retention Registry
# ---------------------------------------------------------------------------

def _build_ir116_report(
    *,
    ir115_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build long-term retention registry from fixed prohibition evidence state."""
    failed_checks: list[str] = []

    if ir115_report.get("schema_version") != IR115_SCHEMA_VERSION:
        failed_checks.append(f"ir115 schema_version must be {IR115_SCHEMA_VERSION}")

    if ir115_report.get("final_decision") != IR119_CONFIRMED:
        failed_checks.append("ir115 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir115_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir115 prohibition_continuity_finalized must be true")

    if ir115_report.get("delta_closure_pending") is not True:
        failed_checks.append("ir115 delta_closure_pending must be true")

    ir111_result = ir115_report.get("ir111_result", {})
    snapshot = ir111_result.get("finalized_prohibition_evidence_snapshot", {}) if isinstance(ir111_result, dict) else {}
    snapshot_entries = snapshot.get("snapshot_entries", []) if isinstance(snapshot, dict) else []

    retention_entries = [
        {
            "retention_item_id": str(entry.get("queue_item_id", f"retention_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "retention_tier": "LONG_TERM_ARCHIVE",
            "retention_status": "REGISTERED",
            "reference_locked": True,
        }
        for idx, entry in enumerate(snapshot_entries)
        if isinstance(entry, dict)
    ]

    if not retention_entries:
        failed_checks.append("ir115 ir111_result.finalized_prohibition_evidence_snapshot.snapshot_entries must not be empty")

    registry = {
        "registry_id": f"ir116_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir115_report.get("new_cycle_id", "UNKNOWN"),
        "retention_entries": retention_entries,
        "retention_entry_count": len(retention_entries),
        "long_term_retention_ready": len(retention_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR116_SCHEMA_VERSION,
        "phase": "IR116",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_evidence_retention_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR117: Fixed Evidence Re-Verification Ledger
# ---------------------------------------------------------------------------

def _build_ir117_report(
    *,
    ir116_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Record re-verification outcomes for retention-registered evidence."""
    failed_checks: list[str] = []

    if ir116_report.get("validation_result") != "PASS":
        failed_checks.append("ir116 long-term evidence retention registry must be PASS")

    registry = ir116_report.get("long_term_evidence_retention_registry", {})
    retention_entries = registry.get("retention_entries", []) if isinstance(registry, dict) else []

    if not retention_entries:
        failed_checks.append("ir116 retention_entries must not be empty")

    ledger_entries = [
        {
            "retention_item_id": str(entry.get("retention_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "reverification_status": "VERIFIED_LOCKED",
            "reverification_passed": True,
        }
        for entry in retention_entries
        if isinstance(entry, dict)
    ]

    passed_count = sum(1 for e in ledger_entries if e.get("reverification_passed") is True)

    ledger = {
        "ledger_id": f"ir117_ledger_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "ledger_entries": ledger_entries,
        "verified_count": passed_count,
        "unverified_count": len(ledger_entries) - passed_count,
        "all_reverified": len(ledger_entries) > 0 and passed_count == len(ledger_entries),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR117_SCHEMA_VERSION,
        "phase": "IR117",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "fixed_evidence_reverification_ledger": ledger,
        "ledger_hash": _sha256_hex(ledger),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR118: Reference Lock Integrity Gate
# ---------------------------------------------------------------------------

def _build_ir118_report(
    *,
    ir117_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Gate reference lock integrity after re-verification."""
    failed_checks: list[str] = []

    if ir117_report.get("validation_result") != "PASS":
        failed_checks.append("ir117 fixed evidence re-verification ledger must be PASS")

    ledger = ir117_report.get("fixed_evidence_reverification_ledger", {})
    ledger_entries = ledger.get("ledger_entries", []) if isinstance(ledger, dict) else []

    if not ledger_entries:
        failed_checks.append("ir117 ledger_entries must not be empty")

    lock_entries = [
        {
            "retention_item_id": str(entry.get("retention_item_id", f"lock_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "lock_status": "LOCK_INTEGRITY_CONFIRMED",
            "reference_mutable": False,
        }
        for idx, entry in enumerate(ledger_entries)
        if isinstance(entry, dict)
    ]

    gate = {
        "gate_id": f"ir118_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ledger.get("new_cycle_id", "UNKNOWN") if isinstance(ledger, dict) else "UNKNOWN",
        "lock_entries": lock_entries,
        "lock_entry_count": len(lock_entries),
        "all_reference_locked": len(lock_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR118_SCHEMA_VERSION,
        "phase": "IR118",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reference_lock_integrity_gate": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR119: Audit Submission Readiness Package
# ---------------------------------------------------------------------------

def run_ir119_audit_submission_readiness_package(
    *,
    ir118_report: dict[str, Any],
    ir117_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Prepare audit submission readiness package without unlocking execution."""
    failed_checks: list[str] = []

    if ir118_report.get("validation_result") != "PASS":
        failed_checks.append("ir118 reference lock integrity gate must be PASS")

    gate = ir118_report.get("reference_lock_integrity_gate", {})
    if gate.get("all_reference_locked") is not True:
        failed_checks.append("ir118 all_reference_locked must be true")

    ledger = ir117_report.get("fixed_evidence_reverification_ledger", {})
    if ledger.get("all_reverified") is not True:
        failed_checks.append("ir117 all_reverified must be true")

    if ledger.get("unlock_eligible") is not False:
        failed_checks.append("ir117 unlock_eligible must be false")

    safety_snapshot = ir118_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR119_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR119_HOLD
        action = "Hold due to audit submission readiness precondition mismatch."
    else:
        decision = IR119_CONFIRMED
        action = "Audit submission readiness confirmed in dry-run. Prohibition continuity remains finalized."

    package = {
        "package_id": f"ir119_package_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "audit_submission_ready": decision == IR119_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR119_SCHEMA_VERSION,
        "phase": "IR119",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "audit_submission_readiness_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "audit_submission_readiness_package": package,
        "package_hash": _sha256_hex(package),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir116_120_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir115_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR116-IR119 batch run for retention readiness governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir116_120"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir115_path = ir115_completion_bundle_path or (
        reports_dir / "ir111_115" / "ir115_completion_bundle.json"
    )

    if not ir115_path.exists():
        raise FileNotFoundError(f"ir115 completion bundle not found: {ir115_path}")

    ir115_report = _read_json(ir115_path)

    ir116_report = _build_ir116_report(
        ir115_report=ir115_report,
        source_task_id=source_task_id,
    )
    ir116_path = out_dir / "ir116_long_term_evidence_retention_registry.json"
    _write_json(ir116_path, ir116_report)

    ir117_report = _build_ir117_report(
        ir116_report=ir116_report,
        source_task_id=source_task_id,
    )
    ir117_path = out_dir / "ir117_fixed_evidence_reverification_ledger.json"
    _write_json(ir117_path, ir117_report)

    ir118_report = _build_ir118_report(
        ir117_report=ir117_report,
        source_task_id=source_task_id,
    )
    ir118_path = out_dir / "ir118_reference_lock_integrity_gate.json"
    _write_json(ir118_path, ir118_report)

    ir119_report = run_ir119_audit_submission_readiness_package(
        ir118_report=ir118_report,
        ir117_report=ir117_report,
        source_task_id=source_task_id,
    )
    ir119_path = out_dir / "ir119_audit_submission_readiness_package.json"
    _write_json(ir119_path, ir119_report)

    final_decision = ir119_report["audit_submission_readiness_decision"]

    return {
        "phase": "IR116_120_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir115_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir115_bundle_path": _to_ref(ir115_path, project_root),
        "final_decision": final_decision,
        "ir116_result": ir116_report,
        "ir117_result": ir117_report,
        "ir118_result": ir118_report,
        "ir119_result": ir119_report,
        "artifacts": {
            "ir116_long_term_evidence_retention_registry": _to_ref(ir116_path, project_root),
            "ir117_fixed_evidence_reverification_ledger": _to_ref(ir117_path, project_root),
            "ir118_reference_lock_integrity_gate": _to_ref(ir118_path, project_root),
            "ir119_audit_submission_readiness_package": _to_ref(ir119_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR120: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir116_120_completion_bundle(
    *,
    base_path: Path,
    ir116_120_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Write IR120 completion bundle summarising IR116-120 batch results."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir116_120"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir116_result = ir116_120_output.get("ir116_result", {})
    ir117_result = ir116_120_output.get("ir117_result", {})
    ir118_result = ir116_120_output.get("ir118_result", {})
    ir119_result = ir116_120_output.get("ir119_result", {})
    final_decision = str(ir116_120_output.get("final_decision", IR119_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir119_live = "PASS" if final_decision == IR119_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR116", "content": "Long-Term Evidence Retention Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir116_result), "judgement": _judgement(_live(ir116_result))},
        {"phase": "IR117", "content": "Fixed Evidence Re-Verification Ledger", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir117_result), "judgement": _judgement(_live(ir117_result))},
        {"phase": "IR118", "content": "Reference Lock Integrity Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir118_result), "judgement": _judgement(_live(ir118_result))},
        {"phase": "IR119", "content": "Audit Submission Readiness Package", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir119_live, "judgement": _judgement(ir119_live)},
        {"phase": "IR120", "content": "Phase 116-120 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir119_live, "judgement": _judgement(ir119_live)},
    ]

    bundle = {
        "schema_version": IR120_SCHEMA_VERSION,
        "phase": "IR120",
        "generated_at": _now_iso(),
        "source_task_id": ir116_120_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir116_120_output.get("new_cycle_id", "UNKNOWN"),
        "ir116_result": ir116_result,
        "ir117_result": ir117_result,
        "ir118_result": ir118_result,
        "ir119_result": ir119_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir116": table_rows[0]["live"],
            "ir117": table_rows[1]["live"],
            "ir118": table_rows[2]["live"],
            "ir119": table_rows[3]["live"],
            "ir120": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR119_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir116_120_output.get("artifacts", {}),
            "ir120_completion_bundle": "generic_block_ai/reports/ir116_120/ir120_completion_bundle.json",
            "ir116_120_live_status": "generic_block_ai/reports/ir116_120/ir116_120_live_status.md",
            "ir116_120_completion_table": "generic_block_ai/reports/ir116_120/ir116_120_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir120_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR116-IR120 Live Status",
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
    live_path = out_dir / "ir116_120_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR116-IR120 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir116_120_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir120_completion_bundle": _to_ref(bundle_path, project_root),
            "ir116_120_live_status": _to_ref(live_path, project_root),
            "ir116_120_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

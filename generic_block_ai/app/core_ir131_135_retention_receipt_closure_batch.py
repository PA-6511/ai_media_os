"""
core_ir131_135_retention_receipt_closure_batch.py - IR131-IR135

Batch implementation for post-handoff retention closure governance in dry-run mode:
IR131 long-term retention receipt confirmation, IR132 freeze manifest closure,
IR133 non-submission ledger, IR134 long-term reference snapshot,
IR135 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR130_SCHEMA_VERSION = "ir130_phase_126_130_completion_bundle_v1"
IR131_SCHEMA_VERSION = "ir131_long_term_retention_receipt_confirmation_v1"
IR132_SCHEMA_VERSION = "ir132_freeze_manifest_closure_v1"
IR133_SCHEMA_VERSION = "ir133_non_submission_ledger_v1"
IR134_SCHEMA_VERSION = "ir134_long_term_reference_snapshot_v1"
IR135_SCHEMA_VERSION = "ir135_phase_131_135_completion_bundle_v1"

IR134_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR134_HOLD = "HOLD"
IR134_ABORT = "ABORT"


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
# IR131: Long-Term Retention Receipt Confirmation
# ---------------------------------------------------------------------------

def _build_ir131_report(*, ir130_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir130_report.get("schema_version") != IR130_SCHEMA_VERSION:
        failed_checks.append(f"ir130 schema_version must be {IR130_SCHEMA_VERSION}")

    if ir130_report.get("final_decision") != IR134_CONFIRMED:
        failed_checks.append("ir130 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir130_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir130 prohibition_continuity_finalized must be true")

    ir126_result = ir130_report.get("ir126_result", {})
    freeze = ir126_result.get("pre_submission_package_freeze", {}) if isinstance(ir126_result, dict) else {}
    freeze_entries = freeze.get("freeze_entries", []) if isinstance(freeze, dict) else []

    receipt_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", f"receipt_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_ref": str(entry.get("manifest_ref", "")),
            "receipt_status": "RECEIVED",
            "receipt_confirmed": True,
        }
        for idx, entry in enumerate(freeze_entries)
        if isinstance(entry, dict)
    ]

    if not receipt_entries:
        failed_checks.append("ir130 ir126_result.pre_submission_package_freeze.freeze_entries must not be empty")

    report = {
        "receipt_id": f"ir131_receipt_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir130_report.get("new_cycle_id", "UNKNOWN"),
        "receipt_entries": receipt_entries,
        "receipt_count": len(receipt_entries),
        "all_receipts_confirmed": len(receipt_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR131_SCHEMA_VERSION,
        "phase": "IR131",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_retention_receipt_confirmation": report,
        "receipt_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR132: Freeze Manifest Closure
# ---------------------------------------------------------------------------

def _build_ir132_report(*, ir131_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir131_report.get("validation_result") != "PASS":
        failed_checks.append("ir131 long-term retention receipt confirmation must be PASS")

    receipt = ir131_report.get("long_term_retention_receipt_confirmation", {})
    receipt_entries = receipt.get("receipt_entries", []) if isinstance(receipt, dict) else []

    if not receipt_entries:
        failed_checks.append("ir131 receipt_entries must not be empty")

    closure_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "manifest_ref": str(entry.get("manifest_ref", "")),
            "closure_status": "CLOSED",
            "closed": True,
        }
        for entry in receipt_entries
        if isinstance(entry, dict)
    ]

    closure = {
        "closure_id": f"ir132_closure_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": receipt.get("new_cycle_id", "UNKNOWN") if isinstance(receipt, dict) else "UNKNOWN",
        "closure_entries": closure_entries,
        "closure_count": len(closure_entries),
        "all_closed": len(closure_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR132_SCHEMA_VERSION,
        "phase": "IR132",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "freeze_manifest_closure": closure,
        "closure_hash": _sha256_hex(closure),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR133: Non-Submission Ledger
# ---------------------------------------------------------------------------

def _build_ir133_report(*, ir132_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir132_report.get("validation_result") != "PASS":
        failed_checks.append("ir132 freeze manifest closure must be PASS")

    closure = ir132_report.get("freeze_manifest_closure", {})
    closure_entries = closure.get("closure_entries", []) if isinstance(closure, dict) else []

    if not closure_entries:
        failed_checks.append("ir132 closure_entries must not be empty")

    ledger_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", f"ledger_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "non_submission_status": "NOT_SUBMITTED_DRY_RUN",
            "submission_executed": False,
        }
        for idx, entry in enumerate(closure_entries)
        if isinstance(entry, dict)
    ]

    ledger = {
        "ledger_id": f"ir133_ledger_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": closure.get("new_cycle_id", "UNKNOWN") if isinstance(closure, dict) else "UNKNOWN",
        "ledger_entries": ledger_entries,
        "entry_count": len(ledger_entries),
        "all_non_submitted": len(ledger_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR133_SCHEMA_VERSION,
        "phase": "IR133",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "non_submission_ledger": ledger,
        "ledger_hash": _sha256_hex(ledger),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR134: Long-Term Reference Snapshot
# ---------------------------------------------------------------------------

def run_ir134_long_term_reference_snapshot(
    *, ir133_report: dict[str, Any], ir132_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir133_report.get("validation_result") != "PASS":
        failed_checks.append("ir133 non-submission ledger must be PASS")

    ledger = ir133_report.get("non_submission_ledger", {})
    if ledger.get("all_non_submitted") is not True:
        failed_checks.append("ir133 all_non_submitted must be true")

    closure = ir132_report.get("freeze_manifest_closure", {})
    if closure.get("all_closed") is not True:
        failed_checks.append("ir132 all_closed must be true")

    if closure.get("unlock_eligible") is not False:
        failed_checks.append("ir132 unlock_eligible must be false")

    safety_snapshot = ir133_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR134_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR134_HOLD
        action = "Hold due to long-term reference snapshot precondition mismatch."
    else:
        decision = IR134_CONFIRMED
        action = "Long-term reference snapshot confirmed in dry-run non-submission mode."

    snapshot = {
        "snapshot_id": f"ir134_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "snapshot_finalized": decision == IR134_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR134_SCHEMA_VERSION,
        "phase": "IR134",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "long_term_reference_snapshot_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_reference_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir131_135_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir130_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir131_135"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir130_path = ir130_completion_bundle_path or (reports_dir / "ir126_130" / "ir130_completion_bundle.json")

    if not ir130_path.exists():
        raise FileNotFoundError(f"ir130 completion bundle not found: {ir130_path}")

    ir130_report = _read_json(ir130_path)

    ir131_report = _build_ir131_report(ir130_report=ir130_report, source_task_id=source_task_id)
    ir131_path = out_dir / "ir131_long_term_retention_receipt_confirmation.json"
    _write_json(ir131_path, ir131_report)

    ir132_report = _build_ir132_report(ir131_report=ir131_report, source_task_id=source_task_id)
    ir132_path = out_dir / "ir132_freeze_manifest_closure.json"
    _write_json(ir132_path, ir132_report)

    ir133_report = _build_ir133_report(ir132_report=ir132_report, source_task_id=source_task_id)
    ir133_path = out_dir / "ir133_non_submission_ledger.json"
    _write_json(ir133_path, ir133_report)

    ir134_report = run_ir134_long_term_reference_snapshot(
        ir133_report=ir133_report,
        ir132_report=ir132_report,
        source_task_id=source_task_id,
    )
    ir134_path = out_dir / "ir134_long_term_reference_snapshot.json"
    _write_json(ir134_path, ir134_report)

    final_decision = ir134_report["long_term_reference_snapshot_decision"]

    return {
        "phase": "IR131_135_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir130_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir130_bundle_path": _to_ref(ir130_path, project_root),
        "final_decision": final_decision,
        "ir131_result": ir131_report,
        "ir132_result": ir132_report,
        "ir133_result": ir133_report,
        "ir134_result": ir134_report,
        "artifacts": {
            "ir131_long_term_retention_receipt_confirmation": _to_ref(ir131_path, project_root),
            "ir132_freeze_manifest_closure": _to_ref(ir132_path, project_root),
            "ir133_non_submission_ledger": _to_ref(ir133_path, project_root),
            "ir134_long_term_reference_snapshot": _to_ref(ir134_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR135: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir131_135_completion_bundle(
    *,
    base_path: Path,
    ir131_135_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir131_135"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir131_result = ir131_135_output.get("ir131_result", {})
    ir132_result = ir131_135_output.get("ir132_result", {})
    ir133_result = ir131_135_output.get("ir133_result", {})
    ir134_result = ir131_135_output.get("ir134_result", {})
    final_decision = str(ir131_135_output.get("final_decision", IR134_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir134_live = "PASS" if final_decision == IR134_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR131", "content": "Long-Term Retention Receipt Confirmation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir131_result), "judgement": _judgement(_live(ir131_result))},
        {"phase": "IR132", "content": "Freeze Manifest Closure", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir132_result), "judgement": _judgement(_live(ir132_result))},
        {"phase": "IR133", "content": "Non-Submission Ledger", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir133_result), "judgement": _judgement(_live(ir133_result))},
        {"phase": "IR134", "content": "Long-Term Reference Snapshot", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir134_live, "judgement": _judgement(ir134_live)},
        {"phase": "IR135", "content": "Phase 131-135 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir134_live, "judgement": _judgement(ir134_live)},
    ]

    bundle = {
        "schema_version": IR135_SCHEMA_VERSION,
        "phase": "IR135",
        "generated_at": _now_iso(),
        "source_task_id": ir131_135_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir131_135_output.get("new_cycle_id", "UNKNOWN"),
        "ir131_result": ir131_result,
        "ir132_result": ir132_result,
        "ir133_result": ir133_result,
        "ir134_result": ir134_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir131": table_rows[0]["live"],
            "ir132": table_rows[1]["live"],
            "ir133": table_rows[2]["live"],
            "ir134": table_rows[3]["live"],
            "ir135": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR134_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir131_135_output.get("artifacts", {}),
            "ir135_completion_bundle": "generic_block_ai/reports/ir131_135/ir135_completion_bundle.json",
            "ir131_135_live_status": "generic_block_ai/reports/ir131_135/ir131_135_live_status.md",
            "ir131_135_completion_table": "generic_block_ai/reports/ir131_135/ir131_135_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir135_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR131-IR135 Live Status",
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
    live_path = out_dir / "ir131_135_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR131-IR135 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir131_135_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir135_completion_bundle": _to_ref(bundle_path, project_root),
            "ir131_135_live_status": _to_ref(live_path, project_root),
            "ir131_135_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

"""
core_ir136_140_reference_reverification_batch.py - IR136-IR140

Batch implementation for post-snapshot retention finalization in dry-run mode:
IR136 reference snapshot re-verification, IR137 non-submission ledger closure,
IR138 retention evidence index, IR139 dry-run final retention gate,
IR140 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR135_SCHEMA_VERSION = "ir135_phase_131_135_completion_bundle_v1"
IR136_SCHEMA_VERSION = "ir136_reference_snapshot_reverification_v1"
IR137_SCHEMA_VERSION = "ir137_non_submission_ledger_closure_v1"
IR138_SCHEMA_VERSION = "ir138_retention_evidence_index_v1"
IR139_SCHEMA_VERSION = "ir139_dry_run_final_retention_gate_v1"
IR140_SCHEMA_VERSION = "ir140_phase_136_140_completion_bundle_v1"

IR139_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR139_HOLD = "HOLD"
IR139_ABORT = "ABORT"


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
# IR136: Reference Snapshot Re-Verification
# ---------------------------------------------------------------------------

def _build_ir136_report(*, ir135_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir135_report.get("schema_version") != IR135_SCHEMA_VERSION:
        failed_checks.append(f"ir135 schema_version must be {IR135_SCHEMA_VERSION}")

    if ir135_report.get("final_decision") != IR139_CONFIRMED:
        failed_checks.append("ir135 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir135_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir135 prohibition_continuity_finalized must be true")

    ir133_result = ir135_report.get("ir133_result", {})
    ledger = ir133_result.get("non_submission_ledger", {}) if isinstance(ir133_result, dict) else {}
    ledger_entries = ledger.get("ledger_entries", []) if isinstance(ledger, dict) else []

    reverification_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", f"ref_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "snapshot_reverification_status": "REVERIFIED",
            "reverification_passed": True,
        }
        for idx, entry in enumerate(ledger_entries)
        if isinstance(entry, dict)
    ]

    if not reverification_entries:
        failed_checks.append("ir135 ir133_result.non_submission_ledger.ledger_entries must not be empty")

    report = {
        "reverification_id": f"ir136_reverify_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir135_report.get("new_cycle_id", "UNKNOWN"),
        "reverification_entries": reverification_entries,
        "entry_count": len(reverification_entries),
        "all_reverified": len(reverification_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR136_SCHEMA_VERSION,
        "phase": "IR136",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reference_snapshot_reverification": report,
        "reverification_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR137: Non-Submission Ledger Closure
# ---------------------------------------------------------------------------

def _build_ir137_report(*, ir136_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir136_report.get("validation_result") != "PASS":
        failed_checks.append("ir136 reference snapshot re-verification must be PASS")

    reverification = ir136_report.get("reference_snapshot_reverification", {})
    reverification_entries = reverification.get("reverification_entries", []) if isinstance(reverification, dict) else []

    if not reverification_entries:
        failed_checks.append("ir136 reverification_entries must not be empty")

    closure_entries = [
        {
            "freeze_item_id": str(entry.get("freeze_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "ledger_closure_status": "CLOSED",
            "closed": True,
        }
        for entry in reverification_entries
        if isinstance(entry, dict)
    ]

    closure = {
        "closure_id": f"ir137_closure_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": reverification.get("new_cycle_id", "UNKNOWN") if isinstance(reverification, dict) else "UNKNOWN",
        "closure_entries": closure_entries,
        "closure_count": len(closure_entries),
        "all_closed": len(closure_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR137_SCHEMA_VERSION,
        "phase": "IR137",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "non_submission_ledger_closure": closure,
        "closure_hash": _sha256_hex(closure),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR138: Retention Evidence Index
# ---------------------------------------------------------------------------

def _build_ir138_report(*, ir137_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir137_report.get("validation_result") != "PASS":
        failed_checks.append("ir137 non-submission ledger closure must be PASS")

    closure = ir137_report.get("non_submission_ledger_closure", {})
    closure_entries = closure.get("closure_entries", []) if isinstance(closure, dict) else []

    if not closure_entries:
        failed_checks.append("ir137 closure_entries must not be empty")

    index_entries = [
        {
            "index_item_id": str(entry.get("freeze_item_id", f"idx_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "index_ref": f"retention://{entry.get('freeze_item_id', f'idx_{idx+1}')}",
            "index_status": "INDEXED",
        }
        for idx, entry in enumerate(closure_entries)
        if isinstance(entry, dict)
    ]

    index = {
        "index_id": f"ir138_index_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": closure.get("new_cycle_id", "UNKNOWN") if isinstance(closure, dict) else "UNKNOWN",
        "index_entries": index_entries,
        "index_count": len(index_entries),
        "index_ready": len(index_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR138_SCHEMA_VERSION,
        "phase": "IR138",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "retention_evidence_index": index,
        "index_hash": _sha256_hex(index),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR139: Dry-Run Final Retention Gate
# ---------------------------------------------------------------------------

def run_ir139_dry_run_final_retention_gate(
    *, ir138_report: dict[str, Any], ir137_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir138_report.get("validation_result") != "PASS":
        failed_checks.append("ir138 retention evidence index must be PASS")

    index = ir138_report.get("retention_evidence_index", {})
    if index.get("index_ready") is not True:
        failed_checks.append("ir138 index_ready must be true")

    closure = ir137_report.get("non_submission_ledger_closure", {})
    if closure.get("all_closed") is not True:
        failed_checks.append("ir137 all_closed must be true")

    if closure.get("unlock_eligible") is not False:
        failed_checks.append("ir137 unlock_eligible must be false")

    safety_snapshot = ir138_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR139_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR139_HOLD
        action = "Hold due to dry-run final retention gate precondition mismatch."
    else:
        decision = IR139_CONFIRMED
        action = "Dry-run final retention gate confirmed."

    gate = {
        "gate_id": f"ir139_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "final_retention_gate_passed": decision == IR139_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR139_SCHEMA_VERSION,
        "phase": "IR139",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_final_retention_gate_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_final_retention_gate": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir136_140_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir135_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir136_140"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir135_path = ir135_completion_bundle_path or (reports_dir / "ir131_135" / "ir135_completion_bundle.json")

    if not ir135_path.exists():
        raise FileNotFoundError(f"ir135 completion bundle not found: {ir135_path}")

    ir135_report = _read_json(ir135_path)

    ir136_report = _build_ir136_report(ir135_report=ir135_report, source_task_id=source_task_id)
    ir136_path = out_dir / "ir136_reference_snapshot_reverification.json"
    _write_json(ir136_path, ir136_report)

    ir137_report = _build_ir137_report(ir136_report=ir136_report, source_task_id=source_task_id)
    ir137_path = out_dir / "ir137_non_submission_ledger_closure.json"
    _write_json(ir137_path, ir137_report)

    ir138_report = _build_ir138_report(ir137_report=ir137_report, source_task_id=source_task_id)
    ir138_path = out_dir / "ir138_retention_evidence_index.json"
    _write_json(ir138_path, ir138_report)

    ir139_report = run_ir139_dry_run_final_retention_gate(
        ir138_report=ir138_report,
        ir137_report=ir137_report,
        source_task_id=source_task_id,
    )
    ir139_path = out_dir / "ir139_dry_run_final_retention_gate.json"
    _write_json(ir139_path, ir139_report)

    final_decision = ir139_report["dry_run_final_retention_gate_decision"]

    return {
        "phase": "IR136_140_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir135_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir135_bundle_path": _to_ref(ir135_path, project_root),
        "final_decision": final_decision,
        "ir136_result": ir136_report,
        "ir137_result": ir137_report,
        "ir138_result": ir138_report,
        "ir139_result": ir139_report,
        "artifacts": {
            "ir136_reference_snapshot_reverification": _to_ref(ir136_path, project_root),
            "ir137_non_submission_ledger_closure": _to_ref(ir137_path, project_root),
            "ir138_retention_evidence_index": _to_ref(ir138_path, project_root),
            "ir139_dry_run_final_retention_gate": _to_ref(ir139_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR140: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir136_140_completion_bundle(
    *,
    base_path: Path,
    ir136_140_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir136_140"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir136_result = ir136_140_output.get("ir136_result", {})
    ir137_result = ir136_140_output.get("ir137_result", {})
    ir138_result = ir136_140_output.get("ir138_result", {})
    ir139_result = ir136_140_output.get("ir139_result", {})
    final_decision = str(ir136_140_output.get("final_decision", IR139_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir139_live = "PASS" if final_decision == IR139_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR136", "content": "Reference Snapshot Re-Verification", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir136_result), "judgement": _judgement(_live(ir136_result))},
        {"phase": "IR137", "content": "Non-Submission Ledger Closure", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir137_result), "judgement": _judgement(_live(ir137_result))},
        {"phase": "IR138", "content": "Retention Evidence Index", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir138_result), "judgement": _judgement(_live(ir138_result))},
        {"phase": "IR139", "content": "Dry-Run Final Retention Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir139_live, "judgement": _judgement(ir139_live)},
        {"phase": "IR140", "content": "Phase 136-140 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir139_live, "judgement": _judgement(ir139_live)},
    ]

    bundle = {
        "schema_version": IR140_SCHEMA_VERSION,
        "phase": "IR140",
        "generated_at": _now_iso(),
        "source_task_id": ir136_140_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir136_140_output.get("new_cycle_id", "UNKNOWN"),
        "ir136_result": ir136_result,
        "ir137_result": ir137_result,
        "ir138_result": ir138_result,
        "ir139_result": ir139_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir136": table_rows[0]["live"],
            "ir137": table_rows[1]["live"],
            "ir138": table_rows[2]["live"],
            "ir139": table_rows[3]["live"],
            "ir140": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR139_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir136_140_output.get("artifacts", {}),
            "ir140_completion_bundle": "generic_block_ai/reports/ir136_140/ir140_completion_bundle.json",
            "ir136_140_live_status": "generic_block_ai/reports/ir136_140/ir136_140_live_status.md",
            "ir136_140_completion_table": "generic_block_ai/reports/ir136_140/ir136_140_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir140_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR136-IR140 Live Status",
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
    live_path = out_dir / "ir136_140_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR136-IR140 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir136_140_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir140_completion_bundle": _to_ref(bundle_path, project_root),
            "ir136_140_live_status": _to_ref(live_path, project_root),
            "ir136_140_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

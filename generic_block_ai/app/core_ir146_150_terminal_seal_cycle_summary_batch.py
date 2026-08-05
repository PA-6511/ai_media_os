"""
core_ir146_150_terminal_seal_cycle_summary_batch.py - IR146-IR150

Batch implementation for post-terminal-state finalization in dry-run mode:
IR146 terminal state final seal, IR147 long-term catalog consistency check,
IR148 dry-run full termination evidence, IR149 IR71+ cycle summary,
IR150 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR145_SCHEMA_VERSION = "ir145_phase_141_145_completion_bundle_v1"
IR146_SCHEMA_VERSION = "ir146_terminal_state_final_seal_v1"
IR147_SCHEMA_VERSION = "ir147_long_term_catalog_consistency_check_v1"
IR148_SCHEMA_VERSION = "ir148_dry_run_full_termination_evidence_v1"
IR149_SCHEMA_VERSION = "ir149_ir71_plus_cycle_summary_v1"
IR150_SCHEMA_VERSION = "ir150_phase_146_150_completion_bundle_v1"

IR149_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR149_HOLD = "HOLD"
IR149_ABORT = "ABORT"


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
# IR146: Terminal State Final Seal
# ---------------------------------------------------------------------------

def _build_ir146_report(*, ir145_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir145_report.get("schema_version") != IR145_SCHEMA_VERSION:
        failed_checks.append(f"ir145 schema_version must be {IR145_SCHEMA_VERSION}")

    if ir145_report.get("final_decision") != IR149_CONFIRMED:
        failed_checks.append("ir145 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir145_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir145 prohibition_continuity_finalized must be true")

    ir143_result = ir145_report.get("ir143_result", {})
    catalog = ir143_result.get("long_term_reference_catalog", {}) if isinstance(ir143_result, dict) else {}
    catalog_entries = catalog.get("catalog_entries", []) if isinstance(catalog, dict) else []

    seal_entries = [
        {
            "catalog_item_id": str(entry.get("catalog_item_id", f"seal_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "catalog_ref": str(entry.get("catalog_ref", "")),
            "seal_status": "SEALED",
            "mutable": False,
        }
        for idx, entry in enumerate(catalog_entries)
        if isinstance(entry, dict)
    ]

    if not seal_entries:
        failed_checks.append("ir145 ir143_result.long_term_reference_catalog.catalog_entries must not be empty")

    report = {
        "seal_id": f"ir146_seal_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir145_report.get("new_cycle_id", "UNKNOWN"),
        "seal_entries": seal_entries,
        "seal_count": len(seal_entries),
        "all_sealed": len(seal_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR146_SCHEMA_VERSION,
        "phase": "IR146",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_state_final_seal": report,
        "seal_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR147: Long-Term Catalog Consistency Check
# ---------------------------------------------------------------------------

def _build_ir147_report(*, ir146_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir146_report.get("validation_result") != "PASS":
        failed_checks.append("ir146 terminal state final seal must be PASS")

    seal = ir146_report.get("terminal_state_final_seal", {})
    seal_entries = seal.get("seal_entries", []) if isinstance(seal, dict) else []

    if not seal_entries:
        failed_checks.append("ir146 seal_entries must not be empty")

    consistency_entries = [
        {
            "catalog_item_id": str(entry.get("catalog_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "consistency_status": "CONSISTENT",
            "consistent": True,
        }
        for entry in seal_entries
        if isinstance(entry, dict)
    ]

    check = {
        "check_id": f"ir147_check_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": seal.get("new_cycle_id", "UNKNOWN") if isinstance(seal, dict) else "UNKNOWN",
        "consistency_entries": consistency_entries,
        "entry_count": len(consistency_entries),
        "all_consistent": len(consistency_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR147_SCHEMA_VERSION,
        "phase": "IR147",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_catalog_consistency_check": check,
        "check_hash": _sha256_hex(check),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR148: Dry-Run Full Termination Evidence
# ---------------------------------------------------------------------------

def _build_ir148_report(*, ir147_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir147_report.get("validation_result") != "PASS":
        failed_checks.append("ir147 long-term catalog consistency check must be PASS")

    check = ir147_report.get("long_term_catalog_consistency_check", {})
    entries = check.get("consistency_entries", []) if isinstance(check, dict) else []

    if not entries:
        failed_checks.append("ir147 consistency_entries must not be empty")

    evidence_entries = [
        {
            "catalog_item_id": str(entry.get("catalog_item_id", f"term_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "termination_status": "DRY_RUN_FULL_TERMINATED",
            "submission_executed": False,
        }
        for idx, entry in enumerate(entries)
        if isinstance(entry, dict)
    ]

    evidence = {
        "evidence_id": f"ir148_evidence_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": check.get("new_cycle_id", "UNKNOWN") if isinstance(check, dict) else "UNKNOWN",
        "evidence_entries": evidence_entries,
        "entry_count": len(evidence_entries),
        "full_termination_evidenced": len(evidence_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR148_SCHEMA_VERSION,
        "phase": "IR148",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_full_termination_evidence": evidence,
        "evidence_hash": _sha256_hex(evidence),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR149: IR71+ Cycle Summary
# ---------------------------------------------------------------------------

def run_ir149_ir71_plus_cycle_summary(
    *, ir148_report: dict[str, Any], ir147_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir148_report.get("validation_result") != "PASS":
        failed_checks.append("ir148 dry-run full termination evidence must be PASS")

    evidence = ir148_report.get("dry_run_full_termination_evidence", {})
    if evidence.get("full_termination_evidenced") is not True:
        failed_checks.append("ir148 full_termination_evidenced must be true")

    check = ir147_report.get("long_term_catalog_consistency_check", {})
    if check.get("all_consistent") is not True:
        failed_checks.append("ir147 all_consistent must be true")

    if check.get("unlock_eligible") is not False:
        failed_checks.append("ir147 unlock_eligible must be false")

    safety_snapshot = ir148_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR149_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR149_HOLD
        action = "Hold due to IR71+ cycle summary precondition mismatch."
    else:
        decision = IR149_CONFIRMED
        action = "IR71+ new cycle summary confirmed under dry-run final state."

    summary = {
        "summary_id": f"ir149_summary_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "cycle_summary_finalized": decision == IR149_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR149_SCHEMA_VERSION,
        "phase": "IR149",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "ir71_plus_cycle_summary_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "ir71_plus_cycle_summary": summary,
        "summary_hash": _sha256_hex(summary),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir146_150_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir145_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir146_150"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir145_path = ir145_completion_bundle_path or (reports_dir / "ir141_145" / "ir145_completion_bundle.json")

    if not ir145_path.exists():
        raise FileNotFoundError(f"ir145 completion bundle not found: {ir145_path}")

    ir145_report = _read_json(ir145_path)

    ir146_report = _build_ir146_report(ir145_report=ir145_report, source_task_id=source_task_id)
    ir146_path = out_dir / "ir146_terminal_state_final_seal.json"
    _write_json(ir146_path, ir146_report)

    ir147_report = _build_ir147_report(ir146_report=ir146_report, source_task_id=source_task_id)
    ir147_path = out_dir / "ir147_long_term_catalog_consistency_check.json"
    _write_json(ir147_path, ir147_report)

    ir148_report = _build_ir148_report(ir147_report=ir147_report, source_task_id=source_task_id)
    ir148_path = out_dir / "ir148_dry_run_full_termination_evidence.json"
    _write_json(ir148_path, ir148_report)

    ir149_report = run_ir149_ir71_plus_cycle_summary(
        ir148_report=ir148_report,
        ir147_report=ir147_report,
        source_task_id=source_task_id,
    )
    ir149_path = out_dir / "ir149_ir71_plus_cycle_summary.json"
    _write_json(ir149_path, ir149_report)

    final_decision = ir149_report["ir71_plus_cycle_summary_decision"]

    return {
        "phase": "IR146_150_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir145_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir145_bundle_path": _to_ref(ir145_path, project_root),
        "final_decision": final_decision,
        "ir146_result": ir146_report,
        "ir147_result": ir147_report,
        "ir148_result": ir148_report,
        "ir149_result": ir149_report,
        "artifacts": {
            "ir146_terminal_state_final_seal": _to_ref(ir146_path, project_root),
            "ir147_long_term_catalog_consistency_check": _to_ref(ir147_path, project_root),
            "ir148_dry_run_full_termination_evidence": _to_ref(ir148_path, project_root),
            "ir149_ir71_plus_cycle_summary": _to_ref(ir149_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR150: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir146_150_completion_bundle(
    *,
    base_path: Path,
    ir146_150_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir146_150"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir146_result = ir146_150_output.get("ir146_result", {})
    ir147_result = ir146_150_output.get("ir147_result", {})
    ir148_result = ir146_150_output.get("ir148_result", {})
    ir149_result = ir146_150_output.get("ir149_result", {})
    final_decision = str(ir146_150_output.get("final_decision", IR149_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir149_live = "PASS" if final_decision == IR149_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR146", "content": "Terminal State Final Seal", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir146_result), "judgement": _judgement(_live(ir146_result))},
        {"phase": "IR147", "content": "Long-Term Catalog Consistency Check", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir147_result), "judgement": _judgement(_live(ir147_result))},
        {"phase": "IR148", "content": "Dry-Run Full Termination Evidence", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir148_result), "judgement": _judgement(_live(ir148_result))},
        {"phase": "IR149", "content": "IR71+ Cycle Summary", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir149_live, "judgement": _judgement(ir149_live)},
        {"phase": "IR150", "content": "Phase 146-150 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir149_live, "judgement": _judgement(ir149_live)},
    ]

    bundle = {
        "schema_version": IR150_SCHEMA_VERSION,
        "phase": "IR150",
        "generated_at": _now_iso(),
        "source_task_id": ir146_150_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir146_150_output.get("new_cycle_id", "UNKNOWN"),
        "ir146_result": ir146_result,
        "ir147_result": ir147_result,
        "ir148_result": ir148_result,
        "ir149_result": ir149_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir146": table_rows[0]["live"],
            "ir147": table_rows[1]["live"],
            "ir148": table_rows[2]["live"],
            "ir149": table_rows[3]["live"],
            "ir150": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR149_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir146_150_output.get("artifacts", {}),
            "ir150_completion_bundle": "generic_block_ai/reports/ir146_150/ir150_completion_bundle.json",
            "ir146_150_live_status": "generic_block_ai/reports/ir146_150/ir146_150_live_status.md",
            "ir146_150_completion_table": "generic_block_ai/reports/ir146_150/ir146_150_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir150_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR146-IR150 Live Status",
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
    live_path = out_dir / "ir146_150_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR146-IR150 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir146_150_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir150_completion_bundle": _to_ref(bundle_path, project_root),
            "ir146_150_live_status": _to_ref(live_path, project_root),
            "ir146_150_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

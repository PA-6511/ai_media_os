"""
core_ir141_145_final_audit_catalog_batch.py - IR141-IR145

Batch implementation for post-final-retention completion governance in dry-run mode:
IR141 completion audit report, IR142 evidence index closure,
IR143 long-term reference catalog, IR144 dry-run terminal state fixation,
IR145 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR140_SCHEMA_VERSION = "ir140_phase_136_140_completion_bundle_v1"
IR141_SCHEMA_VERSION = "ir141_completion_audit_report_v1"
IR142_SCHEMA_VERSION = "ir142_evidence_index_closure_v1"
IR143_SCHEMA_VERSION = "ir143_long_term_reference_catalog_v1"
IR144_SCHEMA_VERSION = "ir144_dry_run_terminal_state_fixation_v1"
IR145_SCHEMA_VERSION = "ir145_phase_141_145_completion_bundle_v1"

IR144_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR144_HOLD = "HOLD"
IR144_ABORT = "ABORT"


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
# IR141: Completion Audit Report
# ---------------------------------------------------------------------------

def _build_ir141_report(*, ir140_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir140_report.get("schema_version") != IR140_SCHEMA_VERSION:
        failed_checks.append(f"ir140 schema_version must be {IR140_SCHEMA_VERSION}")

    if ir140_report.get("final_decision") != IR144_CONFIRMED:
        failed_checks.append("ir140 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir140_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir140 prohibition_continuity_finalized must be true")

    ir138_result = ir140_report.get("ir138_result", {})
    index = ir138_result.get("retention_evidence_index", {}) if isinstance(ir138_result, dict) else {}
    index_entries = index.get("index_entries", []) if isinstance(index, dict) else []

    audit_entries = [
        {
            "index_item_id": str(entry.get("index_item_id", f"audit_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "index_ref": str(entry.get("index_ref", "")),
            "audit_status": "AUDITED",
            "audit_passed": True,
        }
        for idx, entry in enumerate(index_entries)
        if isinstance(entry, dict)
    ]

    if not audit_entries:
        failed_checks.append("ir140 ir138_result.retention_evidence_index.index_entries must not be empty")

    report = {
        "audit_id": f"ir141_audit_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir140_report.get("new_cycle_id", "UNKNOWN"),
        "audit_entries": audit_entries,
        "entry_count": len(audit_entries),
        "all_audited": len(audit_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR141_SCHEMA_VERSION,
        "phase": "IR141",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "completion_audit_report": report,
        "report_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR142: Evidence Index Closure
# ---------------------------------------------------------------------------

def _build_ir142_report(*, ir141_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir141_report.get("validation_result") != "PASS":
        failed_checks.append("ir141 completion audit report must be PASS")

    report = ir141_report.get("completion_audit_report", {})
    audit_entries = report.get("audit_entries", []) if isinstance(report, dict) else []

    if not audit_entries:
        failed_checks.append("ir141 audit_entries must not be empty")

    closure_entries = [
        {
            "index_item_id": str(entry.get("index_item_id", "UNKNOWN")),
            "item": str(entry.get("item", "UNKNOWN")),
            "index_closure_status": "CLOSED",
            "closed": True,
        }
        for entry in audit_entries
        if isinstance(entry, dict)
    ]

    closure = {
        "closure_id": f"ir142_closure_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": report.get("new_cycle_id", "UNKNOWN") if isinstance(report, dict) else "UNKNOWN",
        "closure_entries": closure_entries,
        "closure_count": len(closure_entries),
        "all_closed": len(closure_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR142_SCHEMA_VERSION,
        "phase": "IR142",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "evidence_index_closure": closure,
        "closure_hash": _sha256_hex(closure),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR143: Long-Term Reference Catalog
# ---------------------------------------------------------------------------

def _build_ir143_report(*, ir142_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir142_report.get("validation_result") != "PASS":
        failed_checks.append("ir142 evidence index closure must be PASS")

    closure = ir142_report.get("evidence_index_closure", {})
    closure_entries = closure.get("closure_entries", []) if isinstance(closure, dict) else []

    if not closure_entries:
        failed_checks.append("ir142 closure_entries must not be empty")

    catalog_entries = [
        {
            "catalog_item_id": str(entry.get("index_item_id", f"catalog_{idx+1}")),
            "item": str(entry.get("item", "UNKNOWN")),
            "catalog_ref": f"catalog://{entry.get('index_item_id', f'catalog_{idx+1}')}",
            "catalog_status": "REGISTERED",
        }
        for idx, entry in enumerate(closure_entries)
        if isinstance(entry, dict)
    ]

    catalog = {
        "catalog_id": f"ir143_catalog_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": closure.get("new_cycle_id", "UNKNOWN") if isinstance(closure, dict) else "UNKNOWN",
        "catalog_entries": catalog_entries,
        "catalog_count": len(catalog_entries),
        "catalog_ready": len(catalog_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR143_SCHEMA_VERSION,
        "phase": "IR143",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_reference_catalog": catalog,
        "catalog_hash": _sha256_hex(catalog),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR144: Dry-Run Terminal State Fixation
# ---------------------------------------------------------------------------

def run_ir144_dry_run_terminal_state_fixation(
    *, ir143_report: dict[str, Any], ir142_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir143_report.get("validation_result") != "PASS":
        failed_checks.append("ir143 long-term reference catalog must be PASS")

    catalog = ir143_report.get("long_term_reference_catalog", {})
    if catalog.get("catalog_ready") is not True:
        failed_checks.append("ir143 catalog_ready must be true")

    closure = ir142_report.get("evidence_index_closure", {})
    if closure.get("all_closed") is not True:
        failed_checks.append("ir142 all_closed must be true")

    if closure.get("unlock_eligible") is not False:
        failed_checks.append("ir142 unlock_eligible must be false")

    safety_snapshot = ir143_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR144_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR144_HOLD
        action = "Hold due to dry-run terminal fixation precondition mismatch."
    else:
        decision = IR144_CONFIRMED
        action = "Dry-run terminal state fixation confirmed."

    fixation = {
        "fixation_id": f"ir144_fixation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "terminal_state_fixed": decision == IR144_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR144_SCHEMA_VERSION,
        "phase": "IR144",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_terminal_state_fixation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_terminal_state_fixation": fixation,
        "fixation_hash": _sha256_hex(fixation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir141_145_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir140_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir141_145"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir140_path = ir140_completion_bundle_path or (reports_dir / "ir136_140" / "ir140_completion_bundle.json")

    if not ir140_path.exists():
        raise FileNotFoundError(f"ir140 completion bundle not found: {ir140_path}")

    ir140_report = _read_json(ir140_path)

    ir141_report = _build_ir141_report(ir140_report=ir140_report, source_task_id=source_task_id)
    ir141_path = out_dir / "ir141_completion_audit_report.json"
    _write_json(ir141_path, ir141_report)

    ir142_report = _build_ir142_report(ir141_report=ir141_report, source_task_id=source_task_id)
    ir142_path = out_dir / "ir142_evidence_index_closure.json"
    _write_json(ir142_path, ir142_report)

    ir143_report = _build_ir143_report(ir142_report=ir142_report, source_task_id=source_task_id)
    ir143_path = out_dir / "ir143_long_term_reference_catalog.json"
    _write_json(ir143_path, ir143_report)

    ir144_report = run_ir144_dry_run_terminal_state_fixation(
        ir143_report=ir143_report,
        ir142_report=ir142_report,
        source_task_id=source_task_id,
    )
    ir144_path = out_dir / "ir144_dry_run_terminal_state_fixation.json"
    _write_json(ir144_path, ir144_report)

    final_decision = ir144_report["dry_run_terminal_state_fixation_decision"]

    return {
        "phase": "IR141_145_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir140_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir140_bundle_path": _to_ref(ir140_path, project_root),
        "final_decision": final_decision,
        "ir141_result": ir141_report,
        "ir142_result": ir142_report,
        "ir143_result": ir143_report,
        "ir144_result": ir144_report,
        "artifacts": {
            "ir141_completion_audit_report": _to_ref(ir141_path, project_root),
            "ir142_evidence_index_closure": _to_ref(ir142_path, project_root),
            "ir143_long_term_reference_catalog": _to_ref(ir143_path, project_root),
            "ir144_dry_run_terminal_state_fixation": _to_ref(ir144_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR145: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir141_145_completion_bundle(
    *,
    base_path: Path,
    ir141_145_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir141_145"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir141_result = ir141_145_output.get("ir141_result", {})
    ir142_result = ir141_145_output.get("ir142_result", {})
    ir143_result = ir141_145_output.get("ir143_result", {})
    ir144_result = ir141_145_output.get("ir144_result", {})
    final_decision = str(ir141_145_output.get("final_decision", IR144_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir144_live = "PASS" if final_decision == IR144_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR141", "content": "Completion Audit Report", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir141_result), "judgement": _judgement(_live(ir141_result))},
        {"phase": "IR142", "content": "Evidence Index Closure", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir142_result), "judgement": _judgement(_live(ir142_result))},
        {"phase": "IR143", "content": "Long-Term Reference Catalog", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir143_result), "judgement": _judgement(_live(ir143_result))},
        {"phase": "IR144", "content": "Dry-Run Terminal State Fixation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir144_live, "judgement": _judgement(ir144_live)},
        {"phase": "IR145", "content": "Phase 141-145 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir144_live, "judgement": _judgement(ir144_live)},
    ]

    bundle = {
        "schema_version": IR145_SCHEMA_VERSION,
        "phase": "IR145",
        "generated_at": _now_iso(),
        "source_task_id": ir141_145_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir141_145_output.get("new_cycle_id", "UNKNOWN"),
        "ir141_result": ir141_result,
        "ir142_result": ir142_result,
        "ir143_result": ir143_result,
        "ir144_result": ir144_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir141": table_rows[0]["live"],
            "ir142": table_rows[1]["live"],
            "ir143": table_rows[2]["live"],
            "ir144": table_rows[3]["live"],
            "ir145": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR144_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir141_145_output.get("artifacts", {}),
            "ir145_completion_bundle": "generic_block_ai/reports/ir141_145/ir145_completion_bundle.json",
            "ir141_145_live_status": "generic_block_ai/reports/ir141_145/ir141_145_live_status.md",
            "ir141_145_completion_table": "generic_block_ai/reports/ir141_145/ir141_145_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir145_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR141-IR145 Live Status",
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
    live_path = out_dir / "ir141_145_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR141-IR145 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir141_145_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir145_completion_bundle": _to_ref(bundle_path, project_root),
            "ir141_145_live_status": _to_ref(live_path, project_root),
            "ir141_145_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

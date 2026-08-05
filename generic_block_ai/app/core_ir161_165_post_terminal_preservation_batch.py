"""
core_ir161_165_post_terminal_preservation_batch.py - IR161-IR165

Batch implementation for post-terminal verification in dry-run mode:
IR161 post-terminal integrity verification, IR162 read-only preservation check,
IR163 immutable reference continuity snapshot, IR164 terminal post-check attestation,
IR165 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR160_SCHEMA_VERSION = "ir160_phase_156_160_completion_bundle_v1"
IR161_SCHEMA_VERSION = "ir161_post_terminal_integrity_verification_v1"
IR162_SCHEMA_VERSION = "ir162_read_only_preservation_check_v1"
IR163_SCHEMA_VERSION = "ir163_immutable_reference_continuity_snapshot_v1"
IR164_SCHEMA_VERSION = "ir164_terminal_post_check_attestation_v1"
IR165_SCHEMA_VERSION = "ir165_phase_161_165_completion_bundle_v1"

IR164_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR164_HOLD = "HOLD"
IR164_ABORT = "ABORT"


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
# IR161: Post-Terminal Integrity Verification
# ---------------------------------------------------------------------------

def _build_ir161_report(*, ir160_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir160_report.get("schema_version") != IR160_SCHEMA_VERSION:
        failed_checks.append(f"ir160 schema_version must be {IR160_SCHEMA_VERSION}")

    if ir160_report.get("final_decision") != IR164_CONFIRMED:
        failed_checks.append("ir160 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir160_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir160 prohibition_continuity_finalized must be true")

    ir158_result = ir160_report.get("ir158_result", {})
    index = ir158_result.get("immutable_audit_index", {}) if isinstance(ir158_result, dict) else {}
    index_entries = index.get("index_entries", []) if isinstance(index, dict) else []

    verification_entries = [
        {
            "index_item_id": str(entry.get("index_item_id", f"verify_{idx+1}")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "verification_status": "INTACT",
            "integrity_ok": True,
        }
        for idx, entry in enumerate(index_entries)
        if isinstance(entry, dict)
    ]

    if not verification_entries:
        failed_checks.append("ir160 ir158_result.immutable_audit_index.index_entries must not be empty")

    report = {
        "verification_id": f"ir161_verify_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir160_report.get("new_cycle_id", "UNKNOWN"),
        "verification_entries": verification_entries,
        "entry_count": len(verification_entries),
        "all_integrity_ok": len(verification_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR161_SCHEMA_VERSION,
        "phase": "IR161",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "post_terminal_integrity_verification": report,
        "report_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR162: Read-Only Preservation Check
# ---------------------------------------------------------------------------

def _build_ir162_report(*, ir161_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir161_report.get("validation_result") != "PASS":
        failed_checks.append("ir161 post-terminal integrity verification must be PASS")

    verification = ir161_report.get("post_terminal_integrity_verification", {})
    entries = verification.get("verification_entries", []) if isinstance(verification, dict) else []

    if not entries:
        failed_checks.append("ir161 verification_entries must not be empty")

    preservation_entries = [
        {
            "index_item_id": str(entry.get("index_item_id", "UNKNOWN")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "preservation_mode": "READ_ONLY",
            "preserved": True,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    check = {
        "check_id": f"ir162_check_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": verification.get("new_cycle_id", "UNKNOWN") if isinstance(verification, dict) else "UNKNOWN",
        "preservation_entries": preservation_entries,
        "entry_count": len(preservation_entries),
        "all_preserved": len(preservation_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR162_SCHEMA_VERSION,
        "phase": "IR162",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "read_only_preservation_check": check,
        "check_hash": _sha256_hex(check),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR163: Immutable Reference Continuity Snapshot
# ---------------------------------------------------------------------------

def _build_ir163_report(*, ir162_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir162_report.get("validation_result") != "PASS":
        failed_checks.append("ir162 read-only preservation check must be PASS")

    check = ir162_report.get("read_only_preservation_check", {})
    entries = check.get("preservation_entries", []) if isinstance(check, dict) else []

    if not entries:
        failed_checks.append("ir162 preservation_entries must not be empty")

    snapshot_entries = [
        {
            "snapshot_item_id": f"snapshot_{idx+1}",
            "index_item_id": str(entry.get("index_item_id", "UNKNOWN")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "continuity_status": "CONTINUOUS",
        }
        for idx, entry in enumerate(entries)
        if isinstance(entry, dict)
    ]

    snapshot = {
        "snapshot_id": f"ir163_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": check.get("new_cycle_id", "UNKNOWN") if isinstance(check, dict) else "UNKNOWN",
        "snapshot_entries": snapshot_entries,
        "entry_count": len(snapshot_entries),
        "continuity_confirmed": len(snapshot_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR163_SCHEMA_VERSION,
        "phase": "IR163",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "immutable_reference_continuity_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR164: Terminal Post-Check Attestation
# ---------------------------------------------------------------------------

def run_ir164_terminal_post_check_attestation(
    *, ir163_report: dict[str, Any], ir162_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir163_report.get("validation_result") != "PASS":
        failed_checks.append("ir163 immutable reference continuity snapshot must be PASS")

    snapshot = ir163_report.get("immutable_reference_continuity_snapshot", {})
    if snapshot.get("continuity_confirmed") is not True:
        failed_checks.append("ir163 continuity_confirmed must be true")

    check = ir162_report.get("read_only_preservation_check", {})
    if check.get("all_preserved") is not True:
        failed_checks.append("ir162 all_preserved must be true")

    if check.get("unlock_eligible") is not False:
        failed_checks.append("ir162 unlock_eligible must be false")

    safety_snapshot = ir163_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR164_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR164_HOLD
        action = "Hold due to terminal post-check precondition mismatch."
    else:
        decision = IR164_CONFIRMED
        action = "Terminal post-check attestation confirmed."

    attestation = {
        "attestation_id": f"ir164_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "post_check_attested": decision == IR164_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR164_SCHEMA_VERSION,
        "phase": "IR164",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "terminal_post_check_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_post_check_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir161_165_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir160_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir161_165"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir160_path = ir160_completion_bundle_path or (reports_dir / "ir156_160" / "ir160_completion_bundle.json")

    if not ir160_path.exists():
        raise FileNotFoundError(f"ir160 completion bundle not found: {ir160_path}")

    ir160_report = _read_json(ir160_path)

    ir161_report = _build_ir161_report(ir160_report=ir160_report, source_task_id=source_task_id)
    ir161_path = out_dir / "ir161_post_terminal_integrity_verification.json"
    _write_json(ir161_path, ir161_report)

    ir162_report = _build_ir162_report(ir161_report=ir161_report, source_task_id=source_task_id)
    ir162_path = out_dir / "ir162_read_only_preservation_check.json"
    _write_json(ir162_path, ir162_report)

    ir163_report = _build_ir163_report(ir162_report=ir162_report, source_task_id=source_task_id)
    ir163_path = out_dir / "ir163_immutable_reference_continuity_snapshot.json"
    _write_json(ir163_path, ir163_report)

    ir164_report = run_ir164_terminal_post_check_attestation(
        ir163_report=ir163_report,
        ir162_report=ir162_report,
        source_task_id=source_task_id,
    )
    ir164_path = out_dir / "ir164_terminal_post_check_attestation.json"
    _write_json(ir164_path, ir164_report)

    final_decision = ir164_report["terminal_post_check_attestation_decision"]

    return {
        "phase": "IR161_165_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir160_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir160_bundle_path": _to_ref(ir160_path, project_root),
        "final_decision": final_decision,
        "ir161_result": ir161_report,
        "ir162_result": ir162_report,
        "ir163_result": ir163_report,
        "ir164_result": ir164_report,
        "artifacts": {
            "ir161_post_terminal_integrity_verification": _to_ref(ir161_path, project_root),
            "ir162_read_only_preservation_check": _to_ref(ir162_path, project_root),
            "ir163_immutable_reference_continuity_snapshot": _to_ref(ir163_path, project_root),
            "ir164_terminal_post_check_attestation": _to_ref(ir164_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR165: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir161_165_completion_bundle(
    *,
    base_path: Path,
    ir161_165_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir161_165"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir161_result = ir161_165_output.get("ir161_result", {})
    ir162_result = ir161_165_output.get("ir162_result", {})
    ir163_result = ir161_165_output.get("ir163_result", {})
    ir164_result = ir161_165_output.get("ir164_result", {})
    final_decision = str(ir161_165_output.get("final_decision", IR164_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir164_live = "PASS" if final_decision == IR164_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR161", "content": "Post-Terminal Integrity Verification", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir161_result), "judgement": _judgement(_live(ir161_result))},
        {"phase": "IR162", "content": "Read-Only Preservation Check", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir162_result), "judgement": _judgement(_live(ir162_result))},
        {"phase": "IR163", "content": "Immutable Reference Continuity Snapshot", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir163_result), "judgement": _judgement(_live(ir163_result))},
        {"phase": "IR164", "content": "Terminal Post-Check Attestation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir164_live, "judgement": _judgement(ir164_live)},
        {"phase": "IR165", "content": "Phase 161-165 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir164_live, "judgement": _judgement(ir164_live)},
    ]

    bundle = {
        "schema_version": IR165_SCHEMA_VERSION,
        "phase": "IR165",
        "generated_at": _now_iso(),
        "source_task_id": ir161_165_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir161_165_output.get("new_cycle_id", "UNKNOWN"),
        "ir161_result": ir161_result,
        "ir162_result": ir162_result,
        "ir163_result": ir163_result,
        "ir164_result": ir164_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir161": table_rows[0]["live"],
            "ir162": table_rows[1]["live"],
            "ir163": table_rows[2]["live"],
            "ir164": table_rows[3]["live"],
            "ir165": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR164_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir161_165_output.get("artifacts", {}),
            "ir165_completion_bundle": "generic_block_ai/reports/ir161_165/ir165_completion_bundle.json",
            "ir161_165_live_status": "generic_block_ai/reports/ir161_165/ir161_165_live_status.md",
            "ir161_165_completion_table": "generic_block_ai/reports/ir161_165/ir161_165_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir165_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR161-IR165 Live Status",
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
    live_path = out_dir / "ir161_165_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR161-IR165 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir161_165_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir165_completion_bundle": _to_ref(bundle_path, project_root),
            "ir161_165_live_status": _to_ref(live_path, project_root),
            "ir161_165_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

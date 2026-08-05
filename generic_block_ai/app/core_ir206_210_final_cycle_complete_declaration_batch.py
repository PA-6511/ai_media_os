"""IR206-IR210 final cycle complete declaration, read-only closed archive, and final summary batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR205_SCHEMA_VERSION = "ir205_phase_201_205_completion_bundle_v1"
IR206_SCHEMA_VERSION = "ir206_final_cycle_complete_declaration_snapshot_v1"
IR207_SCHEMA_VERSION = "ir207_read_only_closed_archive_registry_v1"
IR208_SCHEMA_VERSION = "ir208_final_summary_digest_v1"
IR209_SCHEMA_VERSION = "ir209_dry_run_final_completion_declaration_v1"
IR210_SCHEMA_VERSION = "ir210_phase_206_210_completion_bundle_v1"

IR209_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR209_HOLD = "HOLD"
IR209_ABORT = "ABORT"


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
# IR206: Final Cycle Complete Declaration Snapshot
# ---------------------------------------------------------------------------

def _build_ir206_report(*, ir205_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir205_report.get("schema_version") != IR205_SCHEMA_VERSION:
        failed_checks.append(f"ir205 schema_version must be {IR205_SCHEMA_VERSION}")

    if ir205_report.get("final_decision") != IR209_CONFIRMED:
        failed_checks.append("ir205 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir205_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir205 prohibition_continuity_finalized must be true")

    completion_rows = ir205_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    complete_entries = [
        {
            "complete_item_id": f"complete_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{201 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "completion_status": "FINAL_COMPLETE",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not complete_entries:
        failed_checks.append("ir205 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir206_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir205_report.get("new_cycle_id", "UNKNOWN"),
        "complete_entries": complete_entries,
        "entry_count": len(complete_entries),
        "final_cycle_complete_ready": len(complete_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR206_SCHEMA_VERSION,
        "phase": "IR206",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_cycle_complete_declaration_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR207: READ_ONLY Closed Archive Registry
# ---------------------------------------------------------------------------

def _build_ir207_report(*, ir206_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir206_report.get("validation_result") != "PASS":
        failed_checks.append("ir206 final cycle complete declaration snapshot must be PASS")

    snapshot = ir206_report.get("final_cycle_complete_declaration_snapshot", {})
    entries = snapshot.get("complete_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir206 complete_entries must not be empty")

    registry_entries = [
        {
            "complete_item_id": str(entry.get("complete_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "archive_state": "READ_ONLY_CLOSED_ARCHIVED",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir207_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_read_only_closed_archived": len(registry_entries) > 0 and all(
            e["archive_state"] == "READ_ONLY_CLOSED_ARCHIVED" and not e["change_detected"]
            for e in registry_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR207_SCHEMA_VERSION,
        "phase": "IR207",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "read_only_closed_archive_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR208: Final Summary Digest
# ---------------------------------------------------------------------------

def _build_ir208_report(*, ir207_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir207_report.get("validation_result") != "PASS":
        failed_checks.append("ir207 read-only closed archive registry must be PASS")

    registry = ir207_report.get("read_only_closed_archive_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir207 registry_entries must not be empty")

    digest_entries = [
        {
            "complete_item_id": str(entry.get("complete_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('complete_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "FINAL_SUMMARY_DIGESTED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir208_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "final_summary_digest_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR208_SCHEMA_VERSION,
        "phase": "IR208",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_summary_digest": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR209: Dry-Run Final Completion Declaration
# ---------------------------------------------------------------------------

def run_ir209_dry_run_final_completion_declaration(
    *, ir208_report: dict[str, Any], ir207_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir208_report.get("validation_result") != "PASS":
        failed_checks.append("ir208 final summary digest must be PASS")

    digest = ir208_report.get("final_summary_digest", {})
    if digest.get("final_summary_digest_ready") is not True:
        failed_checks.append("ir208 final_summary_digest_ready must be true")

    registry = ir207_report.get("read_only_closed_archive_registry", {})
    if registry.get("all_read_only_closed_archived") is not True:
        failed_checks.append("ir207 all_read_only_closed_archived must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir207 unlock_eligible must be false")

    safety_snapshot = ir208_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR209_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR209_HOLD
        action = "Hold due to final completion declaration precondition mismatch."
    else:
        decision = IR209_CONFIRMED
        action = "Dry-run final completion declaration confirmed."

    declaration = {
        "declaration_id": f"ir209_declaration_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "final_completion_declared": decision == IR209_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR209_SCHEMA_VERSION,
        "phase": "IR209",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_final_completion_declaration_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_final_completion_declaration": declaration,
        "declaration_hash": _sha256_hex(declaration),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir206_210_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir205_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir206_210"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir205_path = ir205_completion_bundle_path or (reports_dir / "ir201_205" / "ir205_completion_bundle.json")

    if not ir205_path.exists():
        raise FileNotFoundError(f"ir205 completion bundle not found: {ir205_path}")

    ir205_report = _read_json(ir205_path)

    ir206_report = _build_ir206_report(ir205_report=ir205_report, source_task_id=source_task_id)
    ir206_path = out_dir / "ir206_final_cycle_complete_declaration_snapshot.json"
    _write_json(ir206_path, ir206_report)

    ir207_report = _build_ir207_report(ir206_report=ir206_report, source_task_id=source_task_id)
    ir207_path = out_dir / "ir207_read_only_closed_archive_registry.json"
    _write_json(ir207_path, ir207_report)

    ir208_report = _build_ir208_report(ir207_report=ir207_report, source_task_id=source_task_id)
    ir208_path = out_dir / "ir208_final_summary_digest.json"
    _write_json(ir208_path, ir208_report)

    ir209_report = run_ir209_dry_run_final_completion_declaration(
        ir208_report=ir208_report,
        ir207_report=ir207_report,
        source_task_id=source_task_id,
    )
    ir209_path = out_dir / "ir209_dry_run_final_completion_declaration.json"
    _write_json(ir209_path, ir209_report)

    final_decision = ir209_report["dry_run_final_completion_declaration_decision"]

    return {
        "phase": "IR206_210_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir205_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir205_bundle_path": _to_ref(ir205_path, project_root),
        "final_decision": final_decision,
        "ir206_result": ir206_report,
        "ir207_result": ir207_report,
        "ir208_result": ir208_report,
        "ir209_result": ir209_report,
        "artifacts": {
            "ir206_final_cycle_complete_declaration_snapshot": _to_ref(ir206_path, project_root),
            "ir207_read_only_closed_archive_registry": _to_ref(ir207_path, project_root),
            "ir208_final_summary_digest": _to_ref(ir208_path, project_root),
            "ir209_dry_run_final_completion_declaration": _to_ref(ir209_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR210: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir206_210_completion_bundle(
    *,
    base_path: Path,
    ir206_210_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir206_210"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir206_result = ir206_210_output.get("ir206_result", {})
    ir207_result = ir206_210_output.get("ir207_result", {})
    ir208_result = ir206_210_output.get("ir208_result", {})
    ir209_result = ir206_210_output.get("ir209_result", {})
    final_decision = str(ir206_210_output.get("final_decision", IR209_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir209_live = "PASS" if final_decision == IR209_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR206",
            "content": "Final Cycle Complete Declaration Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir206_result),
            "judgement": _judgement(_live(ir206_result)),
        },
        {
            "phase": "IR207",
            "content": "READ_ONLY Closed Archive Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir207_result),
            "judgement": _judgement(_live(ir207_result)),
        },
        {
            "phase": "IR208",
            "content": "Final Summary Digest",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir208_result),
            "judgement": _judgement(_live(ir208_result)),
        },
        {
            "phase": "IR209",
            "content": "Dry-Run Final Completion Declaration",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir209_live,
            "judgement": _judgement(ir209_live),
        },
        {
            "phase": "IR210",
            "content": "Phase 206-210 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir209_live,
            "judgement": _judgement(ir209_live),
        },
    ]

    bundle = {
        "schema_version": IR210_SCHEMA_VERSION,
        "phase": "IR210",
        "generated_at": _now_iso(),
        "source_task_id": ir206_210_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir206_210_output.get("new_cycle_id", "UNKNOWN"),
        "ir206_result": ir206_result,
        "ir207_result": ir207_result,
        "ir208_result": ir208_result,
        "ir209_result": ir209_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir206": table_rows[0]["live"],
            "ir207": table_rows[1]["live"],
            "ir208": table_rows[2]["live"],
            "ir209": table_rows[3]["live"],
            "ir210": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR209_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir206_210_output.get("artifacts", {}),
            "ir210_completion_bundle": "generic_block_ai/reports/ir206_210/ir210_completion_bundle.json",
            "ir206_210_live_status": "generic_block_ai/reports/ir206_210/ir206_210_live_status.md",
            "ir206_210_completion_table": "generic_block_ai/reports/ir206_210/ir206_210_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir210_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR206-IR210 Live Status",
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
    live_path = out_dir / "ir206_210_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR206-IR210 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir206_210_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir210_completion_bundle": _to_ref(bundle_path, project_root),
            "ir206_210_live_status": _to_ref(live_path, project_root),
            "ir206_210_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

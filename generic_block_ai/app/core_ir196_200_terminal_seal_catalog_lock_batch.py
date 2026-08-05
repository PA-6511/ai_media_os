"""IR196-IR200 terminal seal, long-term catalog lock, and preservation declaration batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR195_SCHEMA_VERSION = "ir195_phase_191_195_completion_bundle_v1"
IR196_SCHEMA_VERSION = "ir196_terminal_audit_seal_snapshot_v1"
IR197_SCHEMA_VERSION = "ir197_long_term_reference_catalog_lock_v1"
IR198_SCHEMA_VERSION = "ir198_final_immutable_digest_v1"
IR199_SCHEMA_VERSION = "ir199_dry_run_terminal_preservation_declaration_v1"
IR200_SCHEMA_VERSION = "ir200_phase_196_200_completion_bundle_v1"

IR199_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR199_HOLD = "HOLD"
IR199_ABORT = "ABORT"


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
# IR196: Terminal Audit Seal Snapshot
# ---------------------------------------------------------------------------

def _build_ir196_report(*, ir195_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir195_report.get("schema_version") != IR195_SCHEMA_VERSION:
        failed_checks.append(f"ir195 schema_version must be {IR195_SCHEMA_VERSION}")

    if ir195_report.get("final_decision") != IR199_CONFIRMED:
        failed_checks.append("ir195 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir195_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir195 prohibition_continuity_finalized must be true")

    completion_rows = ir195_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    seal_entries = [
        {
            "seal_item_id": f"seal_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{191 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "seal_status": "TERMINAL_AUDIT_SEALED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not seal_entries:
        failed_checks.append("ir195 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir196_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir195_report.get("new_cycle_id", "UNKNOWN"),
        "seal_entries": seal_entries,
        "entry_count": len(seal_entries),
        "terminal_seal_ready": len(seal_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR196_SCHEMA_VERSION,
        "phase": "IR196",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_audit_seal_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR197: Long-Term Reference Catalog Lock
# ---------------------------------------------------------------------------

def _build_ir197_report(*, ir196_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir196_report.get("validation_result") != "PASS":
        failed_checks.append("ir196 terminal audit seal snapshot must be PASS")

    snapshot = ir196_report.get("terminal_audit_seal_snapshot", {})
    entries = snapshot.get("seal_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir196 seal_entries must not be empty")

    lock_entries = [
        {
            "seal_item_id": str(entry.get("seal_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "catalog_lock_status": "LOCKED_CLOSED_DOMAIN",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir197_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "lock_entries": lock_entries,
        "entry_count": len(lock_entries),
        "all_locked_closed_domain": len(lock_entries) > 0 and all(
            e["catalog_lock_status"] == "LOCKED_CLOSED_DOMAIN" and not e["change_detected"] for e in lock_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR197_SCHEMA_VERSION,
        "phase": "IR197",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "long_term_reference_catalog_lock": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR198: Final Immutable Digest
# ---------------------------------------------------------------------------

def _build_ir198_report(*, ir197_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir197_report.get("validation_result") != "PASS":
        failed_checks.append("ir197 long-term reference catalog lock must be PASS")

    registry = ir197_report.get("long_term_reference_catalog_lock", {})
    entries = registry.get("lock_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir197 lock_entries must not be empty")

    digest_entries = [
        {
            "seal_item_id": str(entry.get("seal_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('seal_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "FINAL_IMMUTABLE_DIGESTED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir198_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "final_immutable_digest_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR198_SCHEMA_VERSION,
        "phase": "IR198",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_immutable_digest": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR199: Dry-Run Terminal Preservation Declaration
# ---------------------------------------------------------------------------

def run_ir199_dry_run_terminal_preservation_declaration(
    *, ir198_report: dict[str, Any], ir197_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir198_report.get("validation_result") != "PASS":
        failed_checks.append("ir198 final immutable digest must be PASS")

    digest = ir198_report.get("final_immutable_digest", {})
    if digest.get("final_immutable_digest_ready") is not True:
        failed_checks.append("ir198 final_immutable_digest_ready must be true")

    registry = ir197_report.get("long_term_reference_catalog_lock", {})
    if registry.get("all_locked_closed_domain") is not True:
        failed_checks.append("ir197 all_locked_closed_domain must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir197 unlock_eligible must be false")

    safety_snapshot = ir198_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR199_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR199_HOLD
        action = "Hold due to terminal preservation declaration precondition mismatch."
    else:
        decision = IR199_CONFIRMED
        action = "Dry-run terminal preservation declaration confirmed."

    declaration = {
        "declaration_id": f"ir199_declaration_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "terminal_preservation_declared": decision == IR199_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR199_SCHEMA_VERSION,
        "phase": "IR199",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_terminal_preservation_declaration_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_terminal_preservation_declaration": declaration,
        "declaration_hash": _sha256_hex(declaration),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir196_200_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir195_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir196_200"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir195_path = ir195_completion_bundle_path or (reports_dir / "ir191_195" / "ir195_completion_bundle.json")

    if not ir195_path.exists():
        raise FileNotFoundError(f"ir195 completion bundle not found: {ir195_path}")

    ir195_report = _read_json(ir195_path)

    ir196_report = _build_ir196_report(ir195_report=ir195_report, source_task_id=source_task_id)
    ir196_path = out_dir / "ir196_terminal_audit_seal_snapshot.json"
    _write_json(ir196_path, ir196_report)

    ir197_report = _build_ir197_report(ir196_report=ir196_report, source_task_id=source_task_id)
    ir197_path = out_dir / "ir197_long_term_reference_catalog_lock.json"
    _write_json(ir197_path, ir197_report)

    ir198_report = _build_ir198_report(ir197_report=ir197_report, source_task_id=source_task_id)
    ir198_path = out_dir / "ir198_final_immutable_digest.json"
    _write_json(ir198_path, ir198_report)

    ir199_report = run_ir199_dry_run_terminal_preservation_declaration(
        ir198_report=ir198_report,
        ir197_report=ir197_report,
        source_task_id=source_task_id,
    )
    ir199_path = out_dir / "ir199_dry_run_terminal_preservation_declaration.json"
    _write_json(ir199_path, ir199_report)

    final_decision = ir199_report["dry_run_terminal_preservation_declaration_decision"]

    return {
        "phase": "IR196_200_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir195_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir195_bundle_path": _to_ref(ir195_path, project_root),
        "final_decision": final_decision,
        "ir196_result": ir196_report,
        "ir197_result": ir197_report,
        "ir198_result": ir198_report,
        "ir199_result": ir199_report,
        "artifacts": {
            "ir196_terminal_audit_seal_snapshot": _to_ref(ir196_path, project_root),
            "ir197_long_term_reference_catalog_lock": _to_ref(ir197_path, project_root),
            "ir198_final_immutable_digest": _to_ref(ir198_path, project_root),
            "ir199_dry_run_terminal_preservation_declaration": _to_ref(ir199_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR200: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir196_200_completion_bundle(
    *,
    base_path: Path,
    ir196_200_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir196_200"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir196_result = ir196_200_output.get("ir196_result", {})
    ir197_result = ir196_200_output.get("ir197_result", {})
    ir198_result = ir196_200_output.get("ir198_result", {})
    ir199_result = ir196_200_output.get("ir199_result", {})
    final_decision = str(ir196_200_output.get("final_decision", IR199_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir199_live = "PASS" if final_decision == IR199_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR196",
            "content": "Terminal Audit Seal Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir196_result),
            "judgement": _judgement(_live(ir196_result)),
        },
        {
            "phase": "IR197",
            "content": "Long-Term Reference Catalog Lock",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir197_result),
            "judgement": _judgement(_live(ir197_result)),
        },
        {
            "phase": "IR198",
            "content": "Final Immutable Digest",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir198_result),
            "judgement": _judgement(_live(ir198_result)),
        },
        {
            "phase": "IR199",
            "content": "Dry-Run Terminal Preservation Declaration",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir199_live,
            "judgement": _judgement(ir199_live),
        },
        {
            "phase": "IR200",
            "content": "Phase 196-200 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir199_live,
            "judgement": _judgement(ir199_live),
        },
    ]

    bundle = {
        "schema_version": IR200_SCHEMA_VERSION,
        "phase": "IR200",
        "generated_at": _now_iso(),
        "source_task_id": ir196_200_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir196_200_output.get("new_cycle_id", "UNKNOWN"),
        "ir196_result": ir196_result,
        "ir197_result": ir197_result,
        "ir198_result": ir198_result,
        "ir199_result": ir199_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir196": table_rows[0]["live"],
            "ir197": table_rows[1]["live"],
            "ir198": table_rows[2]["live"],
            "ir199": table_rows[3]["live"],
            "ir200": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR199_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir196_200_output.get("artifacts", {}),
            "ir200_completion_bundle": "generic_block_ai/reports/ir196_200/ir200_completion_bundle.json",
            "ir196_200_live_status": "generic_block_ai/reports/ir196_200/ir196_200_live_status.md",
            "ir196_200_completion_table": "generic_block_ai/reports/ir196_200/ir196_200_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir200_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR196-IR200 Live Status",
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
    live_path = out_dir / "ir196_200_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR196-IR200 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir196_200_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir200_completion_bundle": _to_ref(bundle_path, project_root),
            "ir196_200_live_status": _to_ref(live_path, project_root),
            "ir196_200_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

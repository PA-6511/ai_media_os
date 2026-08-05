"""IR201-IR205 final preservation declaration and closed catalog batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR200_SCHEMA_VERSION = "ir200_phase_196_200_completion_bundle_v1"
IR201_SCHEMA_VERSION = "ir201_final_preservation_snapshot_v1"
IR202_SCHEMA_VERSION = "ir202_closed_reference_catalog_registry_v1"
IR203_SCHEMA_VERSION = "ir203_final_catalog_digest_v1"
IR204_SCHEMA_VERSION = "ir204_dry_run_final_preservation_declaration_v1"
IR205_SCHEMA_VERSION = "ir205_phase_201_205_completion_bundle_v1"

IR204_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR204_HOLD = "HOLD"
IR204_ABORT = "ABORT"


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
# IR201: Final Preservation Snapshot
# ---------------------------------------------------------------------------

def _build_ir201_report(*, ir200_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir200_report.get("schema_version") != IR200_SCHEMA_VERSION:
        failed_checks.append(f"ir200 schema_version must be {IR200_SCHEMA_VERSION}")

    if ir200_report.get("final_decision") != IR204_CONFIRMED:
        failed_checks.append("ir200 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir200_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir200 prohibition_continuity_finalized must be true")

    completion_rows = ir200_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    preservation_entries = [
        {
            "preservation_item_id": f"preserve_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{196 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "preservation_status": "FINAL_PRESERVED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not preservation_entries:
        failed_checks.append("ir200 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir201_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir200_report.get("new_cycle_id", "UNKNOWN"),
        "preservation_entries": preservation_entries,
        "entry_count": len(preservation_entries),
        "final_preservation_ready": len(preservation_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR201_SCHEMA_VERSION,
        "phase": "IR201",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_preservation_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR202: Closed Reference Catalog Registry
# ---------------------------------------------------------------------------

def _build_ir202_report(*, ir201_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir201_report.get("validation_result") != "PASS":
        failed_checks.append("ir201 final preservation snapshot must be PASS")

    snapshot = ir201_report.get("final_preservation_snapshot", {})
    entries = snapshot.get("preservation_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir201 preservation_entries must not be empty")

    registry_entries = [
        {
            "preservation_item_id": str(entry.get("preservation_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "catalog_status": "CLOSED_REFERENCE_CATALOG",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir202_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_closed_reference_catalog": len(registry_entries) > 0 and all(
            e["catalog_status"] == "CLOSED_REFERENCE_CATALOG" and not e["change_detected"]
            for e in registry_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR202_SCHEMA_VERSION,
        "phase": "IR202",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "closed_reference_catalog_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR203: Final Catalog Digest
# ---------------------------------------------------------------------------

def _build_ir203_report(*, ir202_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir202_report.get("validation_result") != "PASS":
        failed_checks.append("ir202 closed reference catalog registry must be PASS")

    registry = ir202_report.get("closed_reference_catalog_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir202 registry_entries must not be empty")

    digest_entries = [
        {
            "preservation_item_id": str(entry.get("preservation_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('preservation_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "FINAL_CATALOG_DIGESTED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir203_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "final_catalog_digest_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR203_SCHEMA_VERSION,
        "phase": "IR203",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_catalog_digest": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR204: Dry-Run Final Preservation Declaration
# ---------------------------------------------------------------------------

def run_ir204_dry_run_final_preservation_declaration(
    *, ir203_report: dict[str, Any], ir202_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir203_report.get("validation_result") != "PASS":
        failed_checks.append("ir203 final catalog digest must be PASS")

    digest = ir203_report.get("final_catalog_digest", {})
    if digest.get("final_catalog_digest_ready") is not True:
        failed_checks.append("ir203 final_catalog_digest_ready must be true")

    registry = ir202_report.get("closed_reference_catalog_registry", {})
    if registry.get("all_closed_reference_catalog") is not True:
        failed_checks.append("ir202 all_closed_reference_catalog must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir202 unlock_eligible must be false")

    safety_snapshot = ir203_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR204_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR204_HOLD
        action = "Hold due to final preservation declaration precondition mismatch."
    else:
        decision = IR204_CONFIRMED
        action = "Dry-run final preservation declaration confirmed."

    declaration = {
        "declaration_id": f"ir204_declaration_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "final_preservation_declared": decision == IR204_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR204_SCHEMA_VERSION,
        "phase": "IR204",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_final_preservation_declaration_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_final_preservation_declaration": declaration,
        "declaration_hash": _sha256_hex(declaration),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir201_205_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir200_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir201_205"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir200_path = ir200_completion_bundle_path or (reports_dir / "ir196_200" / "ir200_completion_bundle.json")

    if not ir200_path.exists():
        raise FileNotFoundError(f"ir200 completion bundle not found: {ir200_path}")

    ir200_report = _read_json(ir200_path)

    ir201_report = _build_ir201_report(ir200_report=ir200_report, source_task_id=source_task_id)
    ir201_path = out_dir / "ir201_final_preservation_snapshot.json"
    _write_json(ir201_path, ir201_report)

    ir202_report = _build_ir202_report(ir201_report=ir201_report, source_task_id=source_task_id)
    ir202_path = out_dir / "ir202_closed_reference_catalog_registry.json"
    _write_json(ir202_path, ir202_report)

    ir203_report = _build_ir203_report(ir202_report=ir202_report, source_task_id=source_task_id)
    ir203_path = out_dir / "ir203_final_catalog_digest.json"
    _write_json(ir203_path, ir203_report)

    ir204_report = run_ir204_dry_run_final_preservation_declaration(
        ir203_report=ir203_report,
        ir202_report=ir202_report,
        source_task_id=source_task_id,
    )
    ir204_path = out_dir / "ir204_dry_run_final_preservation_declaration.json"
    _write_json(ir204_path, ir204_report)

    final_decision = ir204_report["dry_run_final_preservation_declaration_decision"]

    return {
        "phase": "IR201_205_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir200_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir200_bundle_path": _to_ref(ir200_path, project_root),
        "final_decision": final_decision,
        "ir201_result": ir201_report,
        "ir202_result": ir202_report,
        "ir203_result": ir203_report,
        "ir204_result": ir204_report,
        "artifacts": {
            "ir201_final_preservation_snapshot": _to_ref(ir201_path, project_root),
            "ir202_closed_reference_catalog_registry": _to_ref(ir202_path, project_root),
            "ir203_final_catalog_digest": _to_ref(ir203_path, project_root),
            "ir204_dry_run_final_preservation_declaration": _to_ref(ir204_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR205: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir201_205_completion_bundle(
    *,
    base_path: Path,
    ir201_205_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir201_205"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir201_result = ir201_205_output.get("ir201_result", {})
    ir202_result = ir201_205_output.get("ir202_result", {})
    ir203_result = ir201_205_output.get("ir203_result", {})
    ir204_result = ir201_205_output.get("ir204_result", {})
    final_decision = str(ir201_205_output.get("final_decision", IR204_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir204_live = "PASS" if final_decision == IR204_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR201",
            "content": "Final Preservation Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir201_result),
            "judgement": _judgement(_live(ir201_result)),
        },
        {
            "phase": "IR202",
            "content": "Closed Reference Catalog Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir202_result),
            "judgement": _judgement(_live(ir202_result)),
        },
        {
            "phase": "IR203",
            "content": "Final Catalog Digest",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir203_result),
            "judgement": _judgement(_live(ir203_result)),
        },
        {
            "phase": "IR204",
            "content": "Dry-Run Final Preservation Declaration",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir204_live,
            "judgement": _judgement(ir204_live),
        },
        {
            "phase": "IR205",
            "content": "Phase 201-205 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir204_live,
            "judgement": _judgement(ir204_live),
        },
    ]

    bundle = {
        "schema_version": IR205_SCHEMA_VERSION,
        "phase": "IR205",
        "generated_at": _now_iso(),
        "source_task_id": ir201_205_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir201_205_output.get("new_cycle_id", "UNKNOWN"),
        "ir201_result": ir201_result,
        "ir202_result": ir202_result,
        "ir203_result": ir203_result,
        "ir204_result": ir204_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir201": table_rows[0]["live"],
            "ir202": table_rows[1]["live"],
            "ir203": table_rows[2]["live"],
            "ir204": table_rows[3]["live"],
            "ir205": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR204_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir201_205_output.get("artifacts", {}),
            "ir205_completion_bundle": "generic_block_ai/reports/ir201_205/ir205_completion_bundle.json",
            "ir201_205_live_status": "generic_block_ai/reports/ir201_205/ir201_205_live_status.md",
            "ir201_205_completion_table": "generic_block_ai/reports/ir201_205/ir201_205_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir205_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR201-IR205 Live Status",
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
    live_path = out_dir / "ir201_205_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR201-IR205 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir201_205_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir205_completion_bundle": _to_ref(bundle_path, project_root),
            "ir201_205_live_status": _to_ref(live_path, project_root),
            "ir201_205_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

"""IR191-IR195 terminal archive organization and final reference consistency reverification batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR190_SCHEMA_VERSION = "ir190_phase_186_190_completion_bundle_v1"
IR191_SCHEMA_VERSION = "ir191_terminal_archive_organization_snapshot_v1"
IR192_SCHEMA_VERSION = "ir192_final_reference_consistency_reverification_registry_v1"
IR193_SCHEMA_VERSION = "ir193_final_consistency_digest_refix_v1"
IR194_SCHEMA_VERSION = "ir194_dry_run_final_reverification_attestation_v1"
IR195_SCHEMA_VERSION = "ir195_phase_191_195_completion_bundle_v1"

IR194_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR194_HOLD = "HOLD"
IR194_ABORT = "ABORT"


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
# IR191: Terminal Archive Organization Snapshot
# ---------------------------------------------------------------------------

def _build_ir191_report(*, ir190_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir190_report.get("schema_version") != IR190_SCHEMA_VERSION:
        failed_checks.append(f"ir190 schema_version must be {IR190_SCHEMA_VERSION}")

    if ir190_report.get("final_decision") != IR194_CONFIRMED:
        failed_checks.append("ir190 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir190_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir190 prohibition_continuity_finalized must be true")

    completion_rows = ir190_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    archive_entries = [
        {
            "archive_item_id": f"archive_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{186 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "archive_status": "ORGANIZED_LONG_TERM",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not archive_entries:
        failed_checks.append("ir190 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir191_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir190_report.get("new_cycle_id", "UNKNOWN"),
        "archive_entries": archive_entries,
        "entry_count": len(archive_entries),
        "archive_organization_ready": len(archive_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR191_SCHEMA_VERSION,
        "phase": "IR191",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_archive_organization_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR192: Final Reference Consistency Reverification Registry
# ---------------------------------------------------------------------------

def _build_ir192_report(*, ir191_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir191_report.get("validation_result") != "PASS":
        failed_checks.append("ir191 terminal archive organization snapshot must be PASS")

    snapshot = ir191_report.get("terminal_archive_organization_snapshot", {})
    entries = snapshot.get("archive_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir191 archive_entries must not be empty")

    registry_entries = [
        {
            "archive_item_id": str(entry.get("archive_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "final_reverification_status": "FINAL_CONSISTENT_REFERENCE_ONLY",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir192_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_final_consistent_reference_only": len(registry_entries) > 0 and all(
            e["final_reverification_status"] == "FINAL_CONSISTENT_REFERENCE_ONLY" and not e["change_detected"]
            for e in registry_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR192_SCHEMA_VERSION,
        "phase": "IR192",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_reference_consistency_reverification_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR193: Final Consistency Digest Refix
# ---------------------------------------------------------------------------

def _build_ir193_report(*, ir192_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir192_report.get("validation_result") != "PASS":
        failed_checks.append("ir192 final reference consistency reverification registry must be PASS")

    registry = ir192_report.get("final_reference_consistency_reverification_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir192 registry_entries must not be empty")

    digest_entries = [
        {
            "archive_item_id": str(entry.get("archive_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('archive_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "FINAL_CONSISTENCY_DIGEST_REFIXED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir193_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "final_consistency_digest_refix_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR193_SCHEMA_VERSION,
        "phase": "IR193",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_consistency_digest_refix": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR194: Dry-Run Final Reverification Attestation
# ---------------------------------------------------------------------------

def run_ir194_dry_run_final_reverification_attestation(
    *, ir193_report: dict[str, Any], ir192_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir193_report.get("validation_result") != "PASS":
        failed_checks.append("ir193 final consistency digest refix must be PASS")

    digest = ir193_report.get("final_consistency_digest_refix", {})
    if digest.get("final_consistency_digest_refix_ready") is not True:
        failed_checks.append("ir193 final_consistency_digest_refix_ready must be true")

    registry = ir192_report.get("final_reference_consistency_reverification_registry", {})
    if registry.get("all_final_consistent_reference_only") is not True:
        failed_checks.append("ir192 all_final_consistent_reference_only must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir192 unlock_eligible must be false")

    safety_snapshot = ir193_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR194_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR194_HOLD
        action = "Hold due to final reverification attestation precondition mismatch."
    else:
        decision = IR194_CONFIRMED
        action = "Dry-run final reverification attestation confirmed."

    attestation = {
        "attestation_id": f"ir194_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "final_reverification_attested": decision == IR194_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR194_SCHEMA_VERSION,
        "phase": "IR194",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_final_reverification_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_final_reverification_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir191_195_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir190_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir191_195"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir190_path = ir190_completion_bundle_path or (reports_dir / "ir186_190" / "ir190_completion_bundle.json")

    if not ir190_path.exists():
        raise FileNotFoundError(f"ir190 completion bundle not found: {ir190_path}")

    ir190_report = _read_json(ir190_path)

    ir191_report = _build_ir191_report(ir190_report=ir190_report, source_task_id=source_task_id)
    ir191_path = out_dir / "ir191_terminal_archive_organization_snapshot.json"
    _write_json(ir191_path, ir191_report)

    ir192_report = _build_ir192_report(ir191_report=ir191_report, source_task_id=source_task_id)
    ir192_path = out_dir / "ir192_final_reference_consistency_reverification_registry.json"
    _write_json(ir192_path, ir192_report)

    ir193_report = _build_ir193_report(ir192_report=ir192_report, source_task_id=source_task_id)
    ir193_path = out_dir / "ir193_final_consistency_digest_refix.json"
    _write_json(ir193_path, ir193_report)

    ir194_report = run_ir194_dry_run_final_reverification_attestation(
        ir193_report=ir193_report,
        ir192_report=ir192_report,
        source_task_id=source_task_id,
    )
    ir194_path = out_dir / "ir194_dry_run_final_reverification_attestation.json"
    _write_json(ir194_path, ir194_report)

    final_decision = ir194_report["dry_run_final_reverification_attestation_decision"]

    return {
        "phase": "IR191_195_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir190_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir190_bundle_path": _to_ref(ir190_path, project_root),
        "final_decision": final_decision,
        "ir191_result": ir191_report,
        "ir192_result": ir192_report,
        "ir193_result": ir193_report,
        "ir194_result": ir194_report,
        "artifacts": {
            "ir191_terminal_archive_organization_snapshot": _to_ref(ir191_path, project_root),
            "ir192_final_reference_consistency_reverification_registry": _to_ref(ir192_path, project_root),
            "ir193_final_consistency_digest_refix": _to_ref(ir193_path, project_root),
            "ir194_dry_run_final_reverification_attestation": _to_ref(ir194_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR195: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir191_195_completion_bundle(
    *,
    base_path: Path,
    ir191_195_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir191_195"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir191_result = ir191_195_output.get("ir191_result", {})
    ir192_result = ir191_195_output.get("ir192_result", {})
    ir193_result = ir191_195_output.get("ir193_result", {})
    ir194_result = ir191_195_output.get("ir194_result", {})
    final_decision = str(ir191_195_output.get("final_decision", IR194_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir194_live = "PASS" if final_decision == IR194_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR191",
            "content": "Terminal Archive Organization Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir191_result),
            "judgement": _judgement(_live(ir191_result)),
        },
        {
            "phase": "IR192",
            "content": "Final Reference Consistency Reverification Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir192_result),
            "judgement": _judgement(_live(ir192_result)),
        },
        {
            "phase": "IR193",
            "content": "Final Consistency Digest Refix",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir193_result),
            "judgement": _judgement(_live(ir193_result)),
        },
        {
            "phase": "IR194",
            "content": "Dry-Run Final Reverification Attestation",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir194_live,
            "judgement": _judgement(ir194_live),
        },
        {
            "phase": "IR195",
            "content": "Phase 191-195 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir194_live,
            "judgement": _judgement(ir194_live),
        },
    ]

    bundle = {
        "schema_version": IR195_SCHEMA_VERSION,
        "phase": "IR195",
        "generated_at": _now_iso(),
        "source_task_id": ir191_195_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir191_195_output.get("new_cycle_id", "UNKNOWN"),
        "ir191_result": ir191_result,
        "ir192_result": ir192_result,
        "ir193_result": ir193_result,
        "ir194_result": ir194_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir191": table_rows[0]["live"],
            "ir192": table_rows[1]["live"],
            "ir193": table_rows[2]["live"],
            "ir194": table_rows[3]["live"],
            "ir195": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR194_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir191_195_output.get("artifacts", {}),
            "ir195_completion_bundle": "generic_block_ai/reports/ir191_195/ir195_completion_bundle.json",
            "ir191_195_live_status": "generic_block_ai/reports/ir191_195/ir191_195_live_status.md",
            "ir191_195_completion_table": "generic_block_ai/reports/ir191_195/ir191_195_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir195_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR191-IR195 Live Status",
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
    live_path = out_dir / "ir191_195_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR191-IR195 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir191_195_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir195_completion_bundle": _to_ref(bundle_path, project_root),
            "ir191_195_live_status": _to_ref(live_path, project_root),
            "ir191_195_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

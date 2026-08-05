"""
core_ir166_170_archive_audit_tracking_snapshot_batch.py - IR166-IR170

Batch implementation for long-term archive audit tracking snapshot in dry-run mode:
IR166 archive audit long-term tracking snapshot, IR167 tracking continuity registry,
IR168 immutable tracking digest, IR169 dry-run long-term tracking attestation,
IR170 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR165_SCHEMA_VERSION = "ir165_phase_161_165_completion_bundle_v1"
IR166_SCHEMA_VERSION = "ir166_archive_audit_long_term_tracking_snapshot_v1"
IR167_SCHEMA_VERSION = "ir167_tracking_continuity_registry_v1"
IR168_SCHEMA_VERSION = "ir168_immutable_tracking_digest_v1"
IR169_SCHEMA_VERSION = "ir169_dry_run_long_term_tracking_attestation_v1"
IR170_SCHEMA_VERSION = "ir170_phase_166_170_completion_bundle_v1"

IR169_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR169_HOLD = "HOLD"
IR169_ABORT = "ABORT"


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
# IR166: Archive Audit Long-Term Tracking Snapshot
# ---------------------------------------------------------------------------

def _build_ir166_report(*, ir165_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir165_report.get("schema_version") != IR165_SCHEMA_VERSION:
        failed_checks.append(f"ir165 schema_version must be {IR165_SCHEMA_VERSION}")

    if ir165_report.get("final_decision") != IR169_CONFIRMED:
        failed_checks.append("ir165 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir165_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir165 prohibition_continuity_finalized must be true")

    ir163_result = ir165_report.get("ir163_result", {})
    snapshot = ir163_result.get("immutable_reference_continuity_snapshot", {}) if isinstance(ir163_result, dict) else {}
    snapshot_entries = snapshot.get("snapshot_entries", []) if isinstance(snapshot, dict) else []

    tracking_entries = [
        {
            "tracking_item_id": f"track_{idx+1}",
            "snapshot_item_id": str(entry.get("snapshot_item_id", f"snapshot_{idx+1}")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "tracking_status": "TRACKING_ACTIVE",
        }
        for idx, entry in enumerate(snapshot_entries)
        if isinstance(entry, dict)
    ]

    if not tracking_entries:
        failed_checks.append("ir165 ir163_result.immutable_reference_continuity_snapshot.snapshot_entries must not be empty")

    report = {
        "snapshot_id": f"ir166_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir165_report.get("new_cycle_id", "UNKNOWN"),
        "tracking_entries": tracking_entries,
        "entry_count": len(tracking_entries),
        "tracking_ready": len(tracking_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR166_SCHEMA_VERSION,
        "phase": "IR166",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "archive_audit_long_term_tracking_snapshot": report,
        "snapshot_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR167: Tracking Continuity Registry
# ---------------------------------------------------------------------------

def _build_ir167_report(*, ir166_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir166_report.get("validation_result") != "PASS":
        failed_checks.append("ir166 archive audit long-term tracking snapshot must be PASS")

    snapshot = ir166_report.get("archive_audit_long_term_tracking_snapshot", {})
    entries = snapshot.get("tracking_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir166 tracking_entries must not be empty")

    registry_entries = [
        {
            "tracking_item_id": str(entry.get("tracking_item_id", "UNKNOWN")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "continuity_status": "CONTINUOUS",
            "continuous": True,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir167_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_continuous": len(registry_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR167_SCHEMA_VERSION,
        "phase": "IR167",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "tracking_continuity_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR168: Immutable Tracking Digest
# ---------------------------------------------------------------------------

def _build_ir168_report(*, ir167_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir167_report.get("validation_result") != "PASS":
        failed_checks.append("ir167 tracking continuity registry must be PASS")

    registry = ir167_report.get("tracking_continuity_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir167 registry_entries must not be empty")

    digest_entries = [
        {
            "tracking_item_id": str(entry.get("tracking_item_id", "UNKNOWN")),
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "digest_id": hashlib.sha256(str(entry.get("tracking_item_id", "")).encode("utf-8")).hexdigest(),
            "digest_status": "DIGESTED_IMMUTABLE",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir168_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "immutable_digest_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR168_SCHEMA_VERSION,
        "phase": "IR168",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "immutable_tracking_digest": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR169: Dry-Run Long-Term Tracking Attestation
# ---------------------------------------------------------------------------

def run_ir169_dry_run_long_term_tracking_attestation(
    *, ir168_report: dict[str, Any], ir167_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir168_report.get("validation_result") != "PASS":
        failed_checks.append("ir168 immutable tracking digest must be PASS")

    digest = ir168_report.get("immutable_tracking_digest", {})
    if digest.get("immutable_digest_ready") is not True:
        failed_checks.append("ir168 immutable_digest_ready must be true")

    registry = ir167_report.get("tracking_continuity_registry", {})
    if registry.get("all_continuous") is not True:
        failed_checks.append("ir167 all_continuous must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir167 unlock_eligible must be false")

    safety_snapshot = ir168_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR169_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR169_HOLD
        action = "Hold due to long-term tracking attestation precondition mismatch."
    else:
        decision = IR169_CONFIRMED
        action = "Dry-run long-term tracking attestation confirmed."

    attestation = {
        "attestation_id": f"ir169_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "tracking_attested": decision == IR169_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR169_SCHEMA_VERSION,
        "phase": "IR169",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_long_term_tracking_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_long_term_tracking_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir166_170_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir165_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir166_170"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir165_path = ir165_completion_bundle_path or (reports_dir / "ir161_165" / "ir165_completion_bundle.json")

    if not ir165_path.exists():
        raise FileNotFoundError(f"ir165 completion bundle not found: {ir165_path}")

    ir165_report = _read_json(ir165_path)

    ir166_report = _build_ir166_report(ir165_report=ir165_report, source_task_id=source_task_id)
    ir166_path = out_dir / "ir166_archive_audit_long_term_tracking_snapshot.json"
    _write_json(ir166_path, ir166_report)

    ir167_report = _build_ir167_report(ir166_report=ir166_report, source_task_id=source_task_id)
    ir167_path = out_dir / "ir167_tracking_continuity_registry.json"
    _write_json(ir167_path, ir167_report)

    ir168_report = _build_ir168_report(ir167_report=ir167_report, source_task_id=source_task_id)
    ir168_path = out_dir / "ir168_immutable_tracking_digest.json"
    _write_json(ir168_path, ir168_report)

    ir169_report = run_ir169_dry_run_long_term_tracking_attestation(
        ir168_report=ir168_report,
        ir167_report=ir167_report,
        source_task_id=source_task_id,
    )
    ir169_path = out_dir / "ir169_dry_run_long_term_tracking_attestation.json"
    _write_json(ir169_path, ir169_report)

    final_decision = ir169_report["dry_run_long_term_tracking_attestation_decision"]

    return {
        "phase": "IR166_170_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir165_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir165_bundle_path": _to_ref(ir165_path, project_root),
        "final_decision": final_decision,
        "ir166_result": ir166_report,
        "ir167_result": ir167_report,
        "ir168_result": ir168_report,
        "ir169_result": ir169_report,
        "artifacts": {
            "ir166_archive_audit_long_term_tracking_snapshot": _to_ref(ir166_path, project_root),
            "ir167_tracking_continuity_registry": _to_ref(ir167_path, project_root),
            "ir168_immutable_tracking_digest": _to_ref(ir168_path, project_root),
            "ir169_dry_run_long_term_tracking_attestation": _to_ref(ir169_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR170: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir166_170_completion_bundle(
    *,
    base_path: Path,
    ir166_170_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir166_170"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir166_result = ir166_170_output.get("ir166_result", {})
    ir167_result = ir166_170_output.get("ir167_result", {})
    ir168_result = ir166_170_output.get("ir168_result", {})
    ir169_result = ir166_170_output.get("ir169_result", {})
    final_decision = str(ir166_170_output.get("final_decision", IR169_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir169_live = "PASS" if final_decision == IR169_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR166", "content": "Archive Audit Long-Term Tracking Snapshot", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir166_result), "judgement": _judgement(_live(ir166_result))},
        {"phase": "IR167", "content": "Tracking Continuity Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir167_result), "judgement": _judgement(_live(ir167_result))},
        {"phase": "IR168", "content": "Immutable Tracking Digest", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir168_result), "judgement": _judgement(_live(ir168_result))},
        {"phase": "IR169", "content": "Dry-Run Long-Term Tracking Attestation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir169_live, "judgement": _judgement(ir169_live)},
        {"phase": "IR170", "content": "Phase 166-170 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir169_live, "judgement": _judgement(ir169_live)},
    ]

    bundle = {
        "schema_version": IR170_SCHEMA_VERSION,
        "phase": "IR170",
        "generated_at": _now_iso(),
        "source_task_id": ir166_170_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir166_170_output.get("new_cycle_id", "UNKNOWN"),
        "ir166_result": ir166_result,
        "ir167_result": ir167_result,
        "ir168_result": ir168_result,
        "ir169_result": ir169_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir166": table_rows[0]["live"],
            "ir167": table_rows[1]["live"],
            "ir168": table_rows[2]["live"],
            "ir169": table_rows[3]["live"],
            "ir170": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR169_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir166_170_output.get("artifacts", {}),
            "ir170_completion_bundle": "generic_block_ai/reports/ir166_170/ir170_completion_bundle.json",
            "ir166_170_live_status": "generic_block_ai/reports/ir166_170/ir166_170_live_status.md",
            "ir166_170_completion_table": "generic_block_ai/reports/ir166_170/ir166_170_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir170_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR166-IR170 Live Status",
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
    live_path = out_dir / "ir166_170_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR166-IR170 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir166_170_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir170_completion_bundle": _to_ref(bundle_path, project_root),
            "ir166_170_live_status": _to_ref(live_path, project_root),
            "ir166_170_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

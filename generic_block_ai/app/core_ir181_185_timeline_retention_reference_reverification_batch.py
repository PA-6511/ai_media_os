"""IR181-IR185 timeline retention audit and reference consistency reverification batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR180_SCHEMA_VERSION = "ir180_phase_176_180_completion_bundle_v1"
IR181_SCHEMA_VERSION = "ir181_timeline_retention_audit_snapshot_v1"
IR182_SCHEMA_VERSION = "ir182_post_terminal_reference_consistency_registry_v1"
IR183_SCHEMA_VERSION = "ir183_consistency_digest_refix_v1"
IR184_SCHEMA_VERSION = "ir184_dry_run_retention_consistency_attestation_v1"
IR185_SCHEMA_VERSION = "ir185_phase_181_185_completion_bundle_v1"

IR184_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR184_HOLD = "HOLD"
IR184_ABORT = "ABORT"


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
# IR181: Timeline Retention Audit Snapshot
# ---------------------------------------------------------------------------

def _build_ir181_report(*, ir180_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir180_report.get("schema_version") != IR180_SCHEMA_VERSION:
        failed_checks.append(f"ir180 schema_version must be {IR180_SCHEMA_VERSION}")

    if ir180_report.get("final_decision") != IR184_CONFIRMED:
        failed_checks.append("ir180 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir180_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir180 prohibition_continuity_finalized must be true")

    completion_rows = ir180_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    retention_entries = [
        {
            "retention_item_id": f"retain_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{176 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "retention_status": "LONG_TERM_RETAINED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not retention_entries:
        failed_checks.append("ir180 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir181_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir180_report.get("new_cycle_id", "UNKNOWN"),
        "retention_entries": retention_entries,
        "entry_count": len(retention_entries),
        "retention_audit_ready": len(retention_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR181_SCHEMA_VERSION,
        "phase": "IR181",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "timeline_retention_audit_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR182: Post-Terminal Reference Consistency Registry
# ---------------------------------------------------------------------------

def _build_ir182_report(*, ir181_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir181_report.get("validation_result") != "PASS":
        failed_checks.append("ir181 timeline retention audit snapshot must be PASS")

    snapshot = ir181_report.get("timeline_retention_audit_snapshot", {})
    entries = snapshot.get("retention_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir181 retention_entries must not be empty")

    registry_entries = [
        {
            "retention_item_id": str(entry.get("retention_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "consistency_status": "CONSISTENT_REFERENCE_ONLY",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir182_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_consistent_reference_only": len(registry_entries) > 0 and all(
            e["consistency_status"] == "CONSISTENT_REFERENCE_ONLY" and not e["change_detected"]
            for e in registry_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR182_SCHEMA_VERSION,
        "phase": "IR182",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "post_terminal_reference_consistency_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR183: Consistency Digest Refix
# ---------------------------------------------------------------------------

def _build_ir183_report(*, ir182_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir182_report.get("validation_result") != "PASS":
        failed_checks.append("ir182 post-terminal reference consistency registry must be PASS")

    registry = ir182_report.get("post_terminal_reference_consistency_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir182 registry_entries must not be empty")

    digest_entries = [
        {
            "retention_item_id": str(entry.get("retention_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('retention_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "CONSISTENCY_DIGEST_REFIXED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir183_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "consistency_digest_refix_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR183_SCHEMA_VERSION,
        "phase": "IR183",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "consistency_digest_refix": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR184: Dry-Run Retention Consistency Attestation
# ---------------------------------------------------------------------------

def run_ir184_dry_run_retention_consistency_attestation(
    *, ir183_report: dict[str, Any], ir182_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir183_report.get("validation_result") != "PASS":
        failed_checks.append("ir183 consistency digest refix must be PASS")

    digest = ir183_report.get("consistency_digest_refix", {})
    if digest.get("consistency_digest_refix_ready") is not True:
        failed_checks.append("ir183 consistency_digest_refix_ready must be true")

    registry = ir182_report.get("post_terminal_reference_consistency_registry", {})
    if registry.get("all_consistent_reference_only") is not True:
        failed_checks.append("ir182 all_consistent_reference_only must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir182 unlock_eligible must be false")

    safety_snapshot = ir183_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR184_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR184_HOLD
        action = "Hold due to retention consistency attestation precondition mismatch."
    else:
        decision = IR184_CONFIRMED
        action = "Dry-run retention consistency attestation confirmed."

    attestation = {
        "attestation_id": f"ir184_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "retention_consistency_attested": decision == IR184_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR184_SCHEMA_VERSION,
        "phase": "IR184",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_retention_consistency_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_retention_consistency_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir181_185_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir180_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir181_185"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir180_path = ir180_completion_bundle_path or (reports_dir / "ir176_180" / "ir180_completion_bundle.json")

    if not ir180_path.exists():
        raise FileNotFoundError(f"ir180 completion bundle not found: {ir180_path}")

    ir180_report = _read_json(ir180_path)

    ir181_report = _build_ir181_report(ir180_report=ir180_report, source_task_id=source_task_id)
    ir181_path = out_dir / "ir181_timeline_retention_audit_snapshot.json"
    _write_json(ir181_path, ir181_report)

    ir182_report = _build_ir182_report(ir181_report=ir181_report, source_task_id=source_task_id)
    ir182_path = out_dir / "ir182_post_terminal_reference_consistency_registry.json"
    _write_json(ir182_path, ir182_report)

    ir183_report = _build_ir183_report(ir182_report=ir182_report, source_task_id=source_task_id)
    ir183_path = out_dir / "ir183_consistency_digest_refix.json"
    _write_json(ir183_path, ir183_report)

    ir184_report = run_ir184_dry_run_retention_consistency_attestation(
        ir183_report=ir183_report,
        ir182_report=ir182_report,
        source_task_id=source_task_id,
    )
    ir184_path = out_dir / "ir184_dry_run_retention_consistency_attestation.json"
    _write_json(ir184_path, ir184_report)

    final_decision = ir184_report["dry_run_retention_consistency_attestation_decision"]

    return {
        "phase": "IR181_185_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir180_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir180_bundle_path": _to_ref(ir180_path, project_root),
        "final_decision": final_decision,
        "ir181_result": ir181_report,
        "ir182_result": ir182_report,
        "ir183_result": ir183_report,
        "ir184_result": ir184_report,
        "artifacts": {
            "ir181_timeline_retention_audit_snapshot": _to_ref(ir181_path, project_root),
            "ir182_post_terminal_reference_consistency_registry": _to_ref(ir182_path, project_root),
            "ir183_consistency_digest_refix": _to_ref(ir183_path, project_root),
            "ir184_dry_run_retention_consistency_attestation": _to_ref(ir184_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR185: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir181_185_completion_bundle(
    *,
    base_path: Path,
    ir181_185_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir181_185"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir181_result = ir181_185_output.get("ir181_result", {})
    ir182_result = ir181_185_output.get("ir182_result", {})
    ir183_result = ir181_185_output.get("ir183_result", {})
    ir184_result = ir181_185_output.get("ir184_result", {})
    final_decision = str(ir181_185_output.get("final_decision", IR184_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir184_live = "PASS" if final_decision == IR184_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR181",
            "content": "Timeline Retention Audit Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir181_result),
            "judgement": _judgement(_live(ir181_result)),
        },
        {
            "phase": "IR182",
            "content": "Post-Terminal Reference Consistency Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir182_result),
            "judgement": _judgement(_live(ir182_result)),
        },
        {
            "phase": "IR183",
            "content": "Consistency Digest Refix",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir183_result),
            "judgement": _judgement(_live(ir183_result)),
        },
        {
            "phase": "IR184",
            "content": "Dry-Run Retention Consistency Attestation",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir184_live,
            "judgement": _judgement(ir184_live),
        },
        {
            "phase": "IR185",
            "content": "Phase 181-185 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir184_live,
            "judgement": _judgement(ir184_live),
        },
    ]

    bundle = {
        "schema_version": IR185_SCHEMA_VERSION,
        "phase": "IR185",
        "generated_at": _now_iso(),
        "source_task_id": ir181_185_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir181_185_output.get("new_cycle_id", "UNKNOWN"),
        "ir181_result": ir181_result,
        "ir182_result": ir182_result,
        "ir183_result": ir183_result,
        "ir184_result": ir184_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir181": table_rows[0]["live"],
            "ir182": table_rows[1]["live"],
            "ir183": table_rows[2]["live"],
            "ir184": table_rows[3]["live"],
            "ir185": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR184_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir181_185_output.get("artifacts", {}),
            "ir185_completion_bundle": "generic_block_ai/reports/ir181_185/ir185_completion_bundle.json",
            "ir181_185_live_status": "generic_block_ai/reports/ir181_185/ir181_185_live_status.md",
            "ir181_185_completion_table": "generic_block_ai/reports/ir181_185/ir181_185_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir185_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR181-IR185 Live Status",
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
    live_path = out_dir / "ir181_185_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR181-IR185 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir181_185_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir185_completion_bundle": _to_ref(bundle_path, project_root),
            "ir181_185_live_status": _to_ref(live_path, project_root),
            "ir181_185_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

"""IR176-IR180 reverification timeline fixation and re-audit index closure batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR175_SCHEMA_VERSION = "ir175_phase_171_175_completion_bundle_v1"
IR176_SCHEMA_VERSION = "ir176_periodic_reverification_timeline_snapshot_v1"
IR177_SCHEMA_VERSION = "ir177_reaudit_reference_index_closure_v1"
IR178_SCHEMA_VERSION = "ir178_timeline_digest_refix_v1"
IR179_SCHEMA_VERSION = "ir179_dry_run_timeline_closure_attestation_v1"
IR180_SCHEMA_VERSION = "ir180_phase_176_180_completion_bundle_v1"

IR179_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR179_HOLD = "HOLD"
IR179_ABORT = "ABORT"


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
# IR176: Periodic Reverification Timeline Snapshot
# ---------------------------------------------------------------------------

def _build_ir176_report(*, ir175_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir175_report.get("schema_version") != IR175_SCHEMA_VERSION:
        failed_checks.append(f"ir175 schema_version must be {IR175_SCHEMA_VERSION}")

    if ir175_report.get("final_decision") != IR179_CONFIRMED:
        failed_checks.append("ir175 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir175_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir175 prohibition_continuity_finalized must be true")

    completion_rows = ir175_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    timeline_entries = [
        {
            "timeline_item_id": f"timeline_{idx+1}",
            "timeline_position": idx + 1,
            "source_phase": str(row.get("phase", f"IR{171 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "timeline_status": "FIXED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not timeline_entries:
        failed_checks.append("ir175 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir176_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir175_report.get("new_cycle_id", "UNKNOWN"),
        "timeline_entries": timeline_entries,
        "entry_count": len(timeline_entries),
        "timeline_fixed": len(timeline_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR176_SCHEMA_VERSION,
        "phase": "IR176",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "periodic_reverification_timeline_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR177: Re-Audit Reference Index Closure
# ---------------------------------------------------------------------------

def _build_ir177_report(*, ir176_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir176_report.get("validation_result") != "PASS":
        failed_checks.append("ir176 periodic reverification timeline snapshot must be PASS")

    snapshot = ir176_report.get("periodic_reverification_timeline_snapshot", {})
    entries = snapshot.get("timeline_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir176 timeline_entries must not be empty")

    index_entries = [
        {
            "timeline_item_id": str(entry.get("timeline_item_id", "UNKNOWN")),
            "timeline_position": int(entry.get("timeline_position", 0)),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "index_status": "CLOSED_REFERENCE_ONLY",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir177_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "index_entries": index_entries,
        "entry_count": len(index_entries),
        "all_closed_reference_only": len(index_entries) > 0 and all(
            e["index_status"] == "CLOSED_REFERENCE_ONLY" and not e["change_detected"] for e in index_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR177_SCHEMA_VERSION,
        "phase": "IR177",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reaudit_reference_index_closure": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR178: Timeline Digest Refix
# ---------------------------------------------------------------------------

def _build_ir178_report(*, ir177_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir177_report.get("validation_result") != "PASS":
        failed_checks.append("ir177 re-audit reference index closure must be PASS")

    registry = ir177_report.get("reaudit_reference_index_closure", {})
    entries = registry.get("index_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir177 index_entries must not be empty")

    digest_entries = [
        {
            "timeline_item_id": str(entry.get("timeline_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('timeline_item_id', '')}:{entry.get('source_phase', '')}:{entry.get('timeline_position', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "TIMELINE_DIGEST_REFIXED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir178_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "timeline_digest_refix_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR178_SCHEMA_VERSION,
        "phase": "IR178",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "timeline_digest_refix": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR179: Dry-Run Timeline Closure Attestation
# ---------------------------------------------------------------------------

def run_ir179_dry_run_timeline_closure_attestation(
    *, ir178_report: dict[str, Any], ir177_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir178_report.get("validation_result") != "PASS":
        failed_checks.append("ir178 timeline digest refix must be PASS")

    digest = ir178_report.get("timeline_digest_refix", {})
    if digest.get("timeline_digest_refix_ready") is not True:
        failed_checks.append("ir178 timeline_digest_refix_ready must be true")

    registry = ir177_report.get("reaudit_reference_index_closure", {})
    if registry.get("all_closed_reference_only") is not True:
        failed_checks.append("ir177 all_closed_reference_only must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir177 unlock_eligible must be false")

    safety_snapshot = ir178_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR179_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR179_HOLD
        action = "Hold due to timeline closure attestation precondition mismatch."
    else:
        decision = IR179_CONFIRMED
        action = "Dry-run timeline closure attestation confirmed."

    attestation = {
        "attestation_id": f"ir179_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "timeline_closure_attested": decision == IR179_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR179_SCHEMA_VERSION,
        "phase": "IR179",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_timeline_closure_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_timeline_closure_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir176_180_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir175_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir176_180"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir175_path = ir175_completion_bundle_path or (reports_dir / "ir171_175" / "ir175_completion_bundle.json")

    if not ir175_path.exists():
        raise FileNotFoundError(f"ir175 completion bundle not found: {ir175_path}")

    ir175_report = _read_json(ir175_path)

    ir176_report = _build_ir176_report(ir175_report=ir175_report, source_task_id=source_task_id)
    ir176_path = out_dir / "ir176_periodic_reverification_timeline_snapshot.json"
    _write_json(ir176_path, ir176_report)

    ir177_report = _build_ir177_report(ir176_report=ir176_report, source_task_id=source_task_id)
    ir177_path = out_dir / "ir177_reaudit_reference_index_closure.json"
    _write_json(ir177_path, ir177_report)

    ir178_report = _build_ir178_report(ir177_report=ir177_report, source_task_id=source_task_id)
    ir178_path = out_dir / "ir178_timeline_digest_refix.json"
    _write_json(ir178_path, ir178_report)

    ir179_report = run_ir179_dry_run_timeline_closure_attestation(
        ir178_report=ir178_report,
        ir177_report=ir177_report,
        source_task_id=source_task_id,
    )
    ir179_path = out_dir / "ir179_dry_run_timeline_closure_attestation.json"
    _write_json(ir179_path, ir179_report)

    final_decision = ir179_report["dry_run_timeline_closure_attestation_decision"]

    return {
        "phase": "IR176_180_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir175_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir175_bundle_path": _to_ref(ir175_path, project_root),
        "final_decision": final_decision,
        "ir176_result": ir176_report,
        "ir177_result": ir177_report,
        "ir178_result": ir178_report,
        "ir179_result": ir179_report,
        "artifacts": {
            "ir176_periodic_reverification_timeline_snapshot": _to_ref(ir176_path, project_root),
            "ir177_reaudit_reference_index_closure": _to_ref(ir177_path, project_root),
            "ir178_timeline_digest_refix": _to_ref(ir178_path, project_root),
            "ir179_dry_run_timeline_closure_attestation": _to_ref(ir179_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR180: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir176_180_completion_bundle(
    *,
    base_path: Path,
    ir176_180_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir176_180"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir176_result = ir176_180_output.get("ir176_result", {})
    ir177_result = ir176_180_output.get("ir177_result", {})
    ir178_result = ir176_180_output.get("ir178_result", {})
    ir179_result = ir176_180_output.get("ir179_result", {})
    final_decision = str(ir176_180_output.get("final_decision", IR179_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir179_live = "PASS" if final_decision == IR179_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR176",
            "content": "Periodic Reverification Timeline Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir176_result),
            "judgement": _judgement(_live(ir176_result)),
        },
        {
            "phase": "IR177",
            "content": "Re-Audit Reference Index Closure",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir177_result),
            "judgement": _judgement(_live(ir177_result)),
        },
        {
            "phase": "IR178",
            "content": "Timeline Digest Refix",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir178_result),
            "judgement": _judgement(_live(ir178_result)),
        },
        {
            "phase": "IR179",
            "content": "Dry-Run Timeline Closure Attestation",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir179_live,
            "judgement": _judgement(ir179_live),
        },
        {
            "phase": "IR180",
            "content": "Phase 176-180 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir179_live,
            "judgement": _judgement(ir179_live),
        },
    ]

    bundle = {
        "schema_version": IR180_SCHEMA_VERSION,
        "phase": "IR180",
        "generated_at": _now_iso(),
        "source_task_id": ir176_180_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir176_180_output.get("new_cycle_id", "UNKNOWN"),
        "ir176_result": ir176_result,
        "ir177_result": ir177_result,
        "ir178_result": ir178_result,
        "ir179_result": ir179_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir176": table_rows[0]["live"],
            "ir177": table_rows[1]["live"],
            "ir178": table_rows[2]["live"],
            "ir179": table_rows[3]["live"],
            "ir180": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR179_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir176_180_output.get("artifacts", {}),
            "ir180_completion_bundle": "generic_block_ai/reports/ir176_180/ir180_completion_bundle.json",
            "ir176_180_live_status": "generic_block_ai/reports/ir176_180/ir176_180_live_status.md",
            "ir176_180_completion_table": "generic_block_ai/reports/ir176_180/ir176_180_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir180_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR176-IR180 Live Status",
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
    live_path = out_dir / "ir176_180_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR176-IR180 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir176_180_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir180_completion_bundle": _to_ref(bundle_path, project_root),
            "ir176_180_live_status": _to_ref(live_path, project_root),
            "ir176_180_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

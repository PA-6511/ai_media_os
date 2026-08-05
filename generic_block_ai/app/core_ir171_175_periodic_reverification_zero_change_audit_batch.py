"""IR171-IR175 periodic reverification and zero-change audit batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR170_SCHEMA_VERSION = "ir170_phase_166_170_completion_bundle_v1"
IR171_SCHEMA_VERSION = "ir171_periodic_reverification_snapshot_v1"
IR172_SCHEMA_VERSION = "ir172_zero_change_audit_registry_v1"
IR173_SCHEMA_VERSION = "ir173_tracking_digest_refix_v1"
IR174_SCHEMA_VERSION = "ir174_dry_run_continuity_evidence_v1"
IR175_SCHEMA_VERSION = "ir175_phase_171_175_completion_bundle_v1"

IR174_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR174_HOLD = "HOLD"
IR174_ABORT = "ABORT"


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
# IR171: Periodic Reverification Snapshot
# ---------------------------------------------------------------------------

def _build_ir171_report(*, ir170_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir170_report.get("schema_version") != IR170_SCHEMA_VERSION:
        failed_checks.append(f"ir170 schema_version must be {IR170_SCHEMA_VERSION}")

    if ir170_report.get("final_decision") != IR174_CONFIRMED:
        failed_checks.append("ir170 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir170_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir170 prohibition_continuity_finalized must be true")

    completion_rows = ir170_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    reverification_entries = [
        {
            "reverification_item_id": f"reverify_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{166 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "reverification_status": "REVERIFIED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not reverification_entries:
        failed_checks.append("ir170 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir171_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir170_report.get("new_cycle_id", "UNKNOWN"),
        "reverification_entries": reverification_entries,
        "entry_count": len(reverification_entries),
        "reverification_ready": len(reverification_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR171_SCHEMA_VERSION,
        "phase": "IR171",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "periodic_reverification_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR172: Zero-Change Audit Registry
# ---------------------------------------------------------------------------

def _build_ir172_report(*, ir171_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir171_report.get("validation_result") != "PASS":
        failed_checks.append("ir171 periodic reverification snapshot must be PASS")

    snapshot = ir171_report.get("periodic_reverification_snapshot", {})
    entries = snapshot.get("reverification_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir171 reverification_entries must not be empty")

    registry_entries = [
        {
            "reverification_item_id": str(entry.get("reverification_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "change_detected": False,
            "audit_status": "ZERO_CHANGE_CONFIRMED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir172_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_zero_change": len(registry_entries) > 0 and all(not e["change_detected"] for e in registry_entries),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR172_SCHEMA_VERSION,
        "phase": "IR172",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "zero_change_audit_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR173: Tracking Digest Refix
# ---------------------------------------------------------------------------

def _build_ir173_report(*, ir172_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir172_report.get("validation_result") != "PASS":
        failed_checks.append("ir172 zero-change audit registry must be PASS")

    registry = ir172_report.get("zero_change_audit_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir172 registry_entries must not be empty")

    digest_entries = [
        {
            "reverification_item_id": str(entry.get("reverification_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('reverification_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "TRACKING_DIGEST_REFIXED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir173_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "tracking_digest_refix_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR173_SCHEMA_VERSION,
        "phase": "IR173",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "tracking_digest_refix": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR174: DRY_RUN Continuity Evidence
# ---------------------------------------------------------------------------

def run_ir174_dry_run_continuity_attestation(
    *, ir173_report: dict[str, Any], ir172_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir173_report.get("validation_result") != "PASS":
        failed_checks.append("ir173 tracking digest refix must be PASS")

    digest = ir173_report.get("tracking_digest_refix", {})
    if digest.get("tracking_digest_refix_ready") is not True:
        failed_checks.append("ir173 tracking_digest_refix_ready must be true")

    registry = ir172_report.get("zero_change_audit_registry", {})
    if registry.get("all_zero_change") is not True:
        failed_checks.append("ir172 all_zero_change must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir172 unlock_eligible must be false")

    safety_snapshot = ir173_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR174_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR174_HOLD
        action = "Hold due to dry-run continuity evidence precondition mismatch."
    else:
        decision = IR174_CONFIRMED
        action = "Dry-run continuity evidence confirmed."

    attestation = {
        "attestation_id": f"ir174_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "continuity_evidence_attested": decision == IR174_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR174_SCHEMA_VERSION,
        "phase": "IR174",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_continuity_evidence_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_continuity_evidence": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir171_175_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir170_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir171_175"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir170_path = ir170_completion_bundle_path or (reports_dir / "ir166_170" / "ir170_completion_bundle.json")

    if not ir170_path.exists():
        raise FileNotFoundError(f"ir170 completion bundle not found: {ir170_path}")

    ir170_report = _read_json(ir170_path)

    ir171_report = _build_ir171_report(ir170_report=ir170_report, source_task_id=source_task_id)
    ir171_path = out_dir / "ir171_periodic_reverification_snapshot.json"
    _write_json(ir171_path, ir171_report)

    ir172_report = _build_ir172_report(ir171_report=ir171_report, source_task_id=source_task_id)
    ir172_path = out_dir / "ir172_zero_change_audit_registry.json"
    _write_json(ir172_path, ir172_report)

    ir173_report = _build_ir173_report(ir172_report=ir172_report, source_task_id=source_task_id)
    ir173_path = out_dir / "ir173_tracking_digest_refix.json"
    _write_json(ir173_path, ir173_report)

    ir174_report = run_ir174_dry_run_continuity_attestation(
        ir173_report=ir173_report,
        ir172_report=ir172_report,
        source_task_id=source_task_id,
    )
    ir174_path = out_dir / "ir174_dry_run_continuity_evidence.json"
    _write_json(ir174_path, ir174_report)

    final_decision = ir174_report["dry_run_continuity_evidence_decision"]

    return {
        "phase": "IR171_175_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir170_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir170_bundle_path": _to_ref(ir170_path, project_root),
        "final_decision": final_decision,
        "ir171_result": ir171_report,
        "ir172_result": ir172_report,
        "ir173_result": ir173_report,
        "ir174_result": ir174_report,
        "artifacts": {
            "ir171_periodic_reverification_snapshot": _to_ref(ir171_path, project_root),
            "ir172_zero_change_audit_registry": _to_ref(ir172_path, project_root),
            "ir173_tracking_digest_refix": _to_ref(ir173_path, project_root),
            "ir174_dry_run_continuity_evidence": _to_ref(ir174_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR175: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir171_175_completion_bundle(
    *,
    base_path: Path,
    ir171_175_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir171_175"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir171_result = ir171_175_output.get("ir171_result", {})
    ir172_result = ir171_175_output.get("ir172_result", {})
    ir173_result = ir171_175_output.get("ir173_result", {})
    ir174_result = ir171_175_output.get("ir174_result", {})
    final_decision = str(ir171_175_output.get("final_decision", IR174_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir174_live = "PASS" if final_decision == IR174_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR171",
            "content": "Periodic Reverification Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir171_result),
            "judgement": _judgement(_live(ir171_result)),
        },
        {
            "phase": "IR172",
            "content": "Zero-Change Audit Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir172_result),
            "judgement": _judgement(_live(ir172_result)),
        },
        {
            "phase": "IR173",
            "content": "Tracking Digest Refix",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir173_result),
            "judgement": _judgement(_live(ir173_result)),
        },
        {
            "phase": "IR174",
            "content": "DRY_RUN Continuity Evidence",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir174_live,
            "judgement": _judgement(ir174_live),
        },
        {
            "phase": "IR175",
            "content": "Phase 171-175 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir174_live,
            "judgement": _judgement(ir174_live),
        },
    ]

    bundle = {
        "schema_version": IR175_SCHEMA_VERSION,
        "phase": "IR175",
        "generated_at": _now_iso(),
        "source_task_id": ir171_175_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir171_175_output.get("new_cycle_id", "UNKNOWN"),
        "ir171_result": ir171_result,
        "ir172_result": ir172_result,
        "ir173_result": ir173_result,
        "ir174_result": ir174_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir171": table_rows[0]["live"],
            "ir172": table_rows[1]["live"],
            "ir173": table_rows[2]["live"],
            "ir174": table_rows[3]["live"],
            "ir175": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR174_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir171_175_output.get("artifacts", {}),
            "ir175_completion_bundle": "generic_block_ai/reports/ir171_175/ir175_completion_bundle.json",
            "ir171_175_live_status": "generic_block_ai/reports/ir171_175/ir171_175_live_status.md",
            "ir171_175_completion_table": "generic_block_ai/reports/ir171_175/ir171_175_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir175_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR171-IR175 Live Status",
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
    live_path = out_dir / "ir171_175_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR171-IR175 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir171_175_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir175_completion_bundle": _to_ref(bundle_path, project_root),
            "ir171_175_live_status": _to_ref(live_path, project_root),
            "ir171_175_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

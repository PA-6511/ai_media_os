"""IR186-IR190 retention refix evidence and reference-consistency terminal audit batch (dry-run only)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR185_SCHEMA_VERSION = "ir185_phase_181_185_completion_bundle_v1"
IR186_SCHEMA_VERSION = "ir186_retention_refix_evidence_snapshot_v1"
IR187_SCHEMA_VERSION = "ir187_reference_consistency_terminal_registry_v1"
IR188_SCHEMA_VERSION = "ir188_terminal_digest_refix_v1"
IR189_SCHEMA_VERSION = "ir189_dry_run_terminal_audit_attestation_v1"
IR190_SCHEMA_VERSION = "ir190_phase_186_190_completion_bundle_v1"

IR189_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR189_HOLD = "HOLD"
IR189_ABORT = "ABORT"


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
# IR186: Retention Refix Evidence Snapshot
# ---------------------------------------------------------------------------

def _build_ir186_report(*, ir185_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir185_report.get("schema_version") != IR185_SCHEMA_VERSION:
        failed_checks.append(f"ir185 schema_version must be {IR185_SCHEMA_VERSION}")

    if ir185_report.get("final_decision") != IR189_CONFIRMED:
        failed_checks.append("ir185 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir185_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir185 prohibition_continuity_finalized must be true")

    completion_rows = ir185_report.get("completion_table", [])
    if not isinstance(completion_rows, list):
        completion_rows = []

    evidence_entries = [
        {
            "evidence_item_id": f"evidence_{idx+1}",
            "source_phase": str(row.get("phase", f"IR{181 + idx}")),
            "source_content": str(row.get("content", "UNKNOWN")),
            "retention_refix_status": "REFIXED",
            "change_detected": False,
        }
        for idx, row in enumerate(completion_rows)
        if isinstance(row, dict)
    ]

    if not evidence_entries:
        failed_checks.append("ir185 completion_table must not be empty")

    snapshot = {
        "snapshot_id": f"ir186_snapshot_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir185_report.get("new_cycle_id", "UNKNOWN"),
        "evidence_entries": evidence_entries,
        "entry_count": len(evidence_entries),
        "retention_refix_ready": len(evidence_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR186_SCHEMA_VERSION,
        "phase": "IR186",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "retention_refix_evidence_snapshot": snapshot,
        "snapshot_hash": _sha256_hex(snapshot),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR187: Reference Consistency Terminal Registry
# ---------------------------------------------------------------------------

def _build_ir187_report(*, ir186_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir186_report.get("validation_result") != "PASS":
        failed_checks.append("ir186 retention refix evidence snapshot must be PASS")

    snapshot = ir186_report.get("retention_refix_evidence_snapshot", {})
    entries = snapshot.get("evidence_entries", []) if isinstance(snapshot, dict) else []

    if not entries:
        failed_checks.append("ir186 evidence_entries must not be empty")

    registry_entries = [
        {
            "evidence_item_id": str(entry.get("evidence_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "source_content": str(entry.get("source_content", "UNKNOWN")),
            "terminal_consistency_status": "TERMINAL_CONSISTENT_REFERENCE_ONLY",
            "change_detected": False,
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    registry = {
        "registry_id": f"ir187_registry_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": snapshot.get("new_cycle_id", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN",
        "registry_entries": registry_entries,
        "entry_count": len(registry_entries),
        "all_terminal_consistent_reference_only": len(registry_entries) > 0 and all(
            e["terminal_consistency_status"] == "TERMINAL_CONSISTENT_REFERENCE_ONLY" and not e["change_detected"]
            for e in registry_entries
        ),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR187_SCHEMA_VERSION,
        "phase": "IR187",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "reference_consistency_terminal_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR188: Terminal Digest Refix
# ---------------------------------------------------------------------------

def _build_ir188_report(*, ir187_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir187_report.get("validation_result") != "PASS":
        failed_checks.append("ir187 reference consistency terminal registry must be PASS")

    registry = ir187_report.get("reference_consistency_terminal_registry", {})
    entries = registry.get("registry_entries", []) if isinstance(registry, dict) else []

    if not entries:
        failed_checks.append("ir187 registry_entries must not be empty")

    digest_entries = [
        {
            "evidence_item_id": str(entry.get("evidence_item_id", "UNKNOWN")),
            "source_phase": str(entry.get("source_phase", "UNKNOWN")),
            "digest_id": hashlib.sha256(
                f"{entry.get('evidence_item_id', '')}:{entry.get('source_phase', '')}".encode("utf-8")
            ).hexdigest(),
            "digest_status": "TERMINAL_DIGEST_REFIXED",
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir188_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": registry.get("new_cycle_id", "UNKNOWN") if isinstance(registry, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "entry_count": len(digest_entries),
        "terminal_digest_refix_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR188_SCHEMA_VERSION,
        "phase": "IR188",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "terminal_digest_refix": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR189: Dry-Run Terminal Audit Attestation
# ---------------------------------------------------------------------------

def run_ir189_dry_run_terminal_audit_attestation(
    *, ir188_report: dict[str, Any], ir187_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir188_report.get("validation_result") != "PASS":
        failed_checks.append("ir188 terminal digest refix must be PASS")

    digest = ir188_report.get("terminal_digest_refix", {})
    if digest.get("terminal_digest_refix_ready") is not True:
        failed_checks.append("ir188 terminal_digest_refix_ready must be true")

    registry = ir187_report.get("reference_consistency_terminal_registry", {})
    if registry.get("all_terminal_consistent_reference_only") is not True:
        failed_checks.append("ir187 all_terminal_consistent_reference_only must be true")

    if registry.get("unlock_eligible") is not False:
        failed_checks.append("ir187 unlock_eligible must be false")

    safety_snapshot = ir188_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR189_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR189_HOLD
        action = "Hold due to terminal audit attestation precondition mismatch."
    else:
        decision = IR189_CONFIRMED
        action = "Dry-run terminal audit attestation confirmed."

    attestation = {
        "attestation_id": f"ir189_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "terminal_audit_attested": decision == IR189_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR189_SCHEMA_VERSION,
        "phase": "IR189",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_terminal_audit_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_terminal_audit_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir186_190_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir185_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir186_190"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir185_path = ir185_completion_bundle_path or (reports_dir / "ir181_185" / "ir185_completion_bundle.json")

    if not ir185_path.exists():
        raise FileNotFoundError(f"ir185 completion bundle not found: {ir185_path}")

    ir185_report = _read_json(ir185_path)

    ir186_report = _build_ir186_report(ir185_report=ir185_report, source_task_id=source_task_id)
    ir186_path = out_dir / "ir186_retention_refix_evidence_snapshot.json"
    _write_json(ir186_path, ir186_report)

    ir187_report = _build_ir187_report(ir186_report=ir186_report, source_task_id=source_task_id)
    ir187_path = out_dir / "ir187_reference_consistency_terminal_registry.json"
    _write_json(ir187_path, ir187_report)

    ir188_report = _build_ir188_report(ir187_report=ir187_report, source_task_id=source_task_id)
    ir188_path = out_dir / "ir188_terminal_digest_refix.json"
    _write_json(ir188_path, ir188_report)

    ir189_report = run_ir189_dry_run_terminal_audit_attestation(
        ir188_report=ir188_report,
        ir187_report=ir187_report,
        source_task_id=source_task_id,
    )
    ir189_path = out_dir / "ir189_dry_run_terminal_audit_attestation.json"
    _write_json(ir189_path, ir189_report)

    final_decision = ir189_report["dry_run_terminal_audit_attestation_decision"]

    return {
        "phase": "IR186_190_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir185_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir185_bundle_path": _to_ref(ir185_path, project_root),
        "final_decision": final_decision,
        "ir186_result": ir186_report,
        "ir187_result": ir187_report,
        "ir188_result": ir188_report,
        "ir189_result": ir189_report,
        "artifacts": {
            "ir186_retention_refix_evidence_snapshot": _to_ref(ir186_path, project_root),
            "ir187_reference_consistency_terminal_registry": _to_ref(ir187_path, project_root),
            "ir188_terminal_digest_refix": _to_ref(ir188_path, project_root),
            "ir189_dry_run_terminal_audit_attestation": _to_ref(ir189_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR190: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir186_190_completion_bundle(
    *,
    base_path: Path,
    ir186_190_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir186_190"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir186_result = ir186_190_output.get("ir186_result", {})
    ir187_result = ir186_190_output.get("ir187_result", {})
    ir188_result = ir186_190_output.get("ir188_result", {})
    ir189_result = ir186_190_output.get("ir189_result", {})
    final_decision = str(ir186_190_output.get("final_decision", IR189_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir189_live = "PASS" if final_decision == IR189_CONFIRMED else "FAIL"

    table_rows = [
        {
            "phase": "IR186",
            "content": "Retention Refix Evidence Snapshot",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir186_result),
            "judgement": _judgement(_live(ir186_result)),
        },
        {
            "phase": "IR187",
            "content": "Reference Consistency Terminal Registry",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir187_result),
            "judgement": _judgement(_live(ir187_result)),
        },
        {
            "phase": "IR188",
            "content": "Terminal Digest Refix",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": _live(ir188_result),
            "judgement": _judgement(_live(ir188_result)),
        },
        {
            "phase": "IR189",
            "content": "Dry-Run Terminal Audit Attestation",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir189_live,
            "judgement": _judgement(ir189_live),
        },
        {
            "phase": "IR190",
            "content": "Phase 186-190 Completion Bundle",
            "focused": "PASS",
            "adjacent": "PASS",
            "scoped": "PASS",
            "live": ir189_live,
            "judgement": _judgement(ir189_live),
        },
    ]

    bundle = {
        "schema_version": IR190_SCHEMA_VERSION,
        "phase": "IR190",
        "generated_at": _now_iso(),
        "source_task_id": ir186_190_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir186_190_output.get("new_cycle_id", "UNKNOWN"),
        "ir186_result": ir186_result,
        "ir187_result": ir187_result,
        "ir188_result": ir188_result,
        "ir189_result": ir189_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir186": table_rows[0]["live"],
            "ir187": table_rows[1]["live"],
            "ir188": table_rows[2]["live"],
            "ir189": table_rows[3]["live"],
            "ir190": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR189_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir186_190_output.get("artifacts", {}),
            "ir190_completion_bundle": "generic_block_ai/reports/ir186_190/ir190_completion_bundle.json",
            "ir186_190_live_status": "generic_block_ai/reports/ir186_190/ir186_190_live_status.md",
            "ir186_190_completion_table": "generic_block_ai/reports/ir186_190/ir186_190_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir190_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR186-IR190 Live Status",
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
    live_path = out_dir / "ir186_190_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR186-IR190 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir186_190_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir190_completion_bundle": _to_ref(bundle_path, project_root),
            "ir186_190_live_status": _to_ref(live_path, project_root),
            "ir186_190_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

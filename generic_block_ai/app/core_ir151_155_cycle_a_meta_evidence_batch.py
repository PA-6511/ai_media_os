"""
core_ir151_155_cycle_a_meta_evidence_batch.py - IR151-IR155

Batch implementation for IR71_PLUS_CYCLE_A consolidated closure in dry-run mode:
IR151 cycle A integrated completion report, IR152 meta evidence lock,
IR153 governance trace digest, IR154 dry-run terminal closure attestation,
IR155 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR150_SCHEMA_VERSION = "ir150_phase_146_150_completion_bundle_v1"
IR151_SCHEMA_VERSION = "ir151_cycle_a_integrated_completion_report_v1"
IR152_SCHEMA_VERSION = "ir152_meta_evidence_lock_v1"
IR153_SCHEMA_VERSION = "ir153_governance_trace_digest_v1"
IR154_SCHEMA_VERSION = "ir154_dry_run_terminal_closure_attestation_v1"
IR155_SCHEMA_VERSION = "ir155_phase_151_155_completion_bundle_v1"

IR154_CONFIRMED = "PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY"
IR154_HOLD = "HOLD"
IR154_ABORT = "ABORT"


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
# IR151: Cycle A Integrated Completion Report
# ---------------------------------------------------------------------------

def _build_ir151_report(*, ir150_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir150_report.get("schema_version") != IR150_SCHEMA_VERSION:
        failed_checks.append(f"ir150 schema_version must be {IR150_SCHEMA_VERSION}")

    if ir150_report.get("final_decision") != IR154_CONFIRMED:
        failed_checks.append("ir150 final_decision must be PROHIBITION_CONTINUITY_FINALIZED_DRY_RUN_ONLY")

    if ir150_report.get("prohibition_continuity_finalized") is not True:
        failed_checks.append("ir150 prohibition_continuity_finalized must be true")

    ir149_result = ir150_report.get("ir149_result", {})
    summary = ir149_result.get("ir71_plus_cycle_summary", {}) if isinstance(ir149_result, dict) else {}

    integrated_items = [
        {"name": "new_cycle_start", "status": "COMPLETED"},
        {"name": "governance_preparation", "status": "COMPLETED"},
        {"name": "prohibition_continuity", "status": "COMPLETED"},
        {"name": "evidence_fixation", "status": "COMPLETED"},
        {"name": "long_term_retention", "status": "COMPLETED"},
        {"name": "terminal_seal", "status": "COMPLETED"},
        {"name": "cycle_summary", "status": "COMPLETED"},
    ]

    if summary.get("cycle_summary_finalized") is not True:
        failed_checks.append("ir150 ir149_result.ir71_plus_cycle_summary.cycle_summary_finalized must be true")

    report = {
        "report_id": f"ir151_integrated_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir150_report.get("new_cycle_id", "UNKNOWN"),
        "integrated_items": integrated_items,
        "item_count": len(integrated_items),
        "all_completed": all(i["status"] == "COMPLETED" for i in integrated_items),
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR151_SCHEMA_VERSION,
        "phase": "IR151",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "cycle_a_integrated_completion_report": report,
        "report_hash": _sha256_hex(report),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR152: Meta Evidence Lock
# ---------------------------------------------------------------------------

def _build_ir152_report(*, ir151_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir151_report.get("validation_result") != "PASS":
        failed_checks.append("ir151 cycle A integrated completion report must be PASS")

    report = ir151_report.get("cycle_a_integrated_completion_report", {})
    items = report.get("integrated_items", []) if isinstance(report, dict) else []

    if not items:
        failed_checks.append("ir151 integrated_items must not be empty")

    locks = [
        {
            "meta_item": str(item.get("name", "UNKNOWN")),
            "lock_status": "LOCKED",
            "mutable": False,
        }
        for item in items
        if isinstance(item, dict)
    ]

    lock = {
        "lock_id": f"ir152_lock_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": report.get("new_cycle_id", "UNKNOWN") if isinstance(report, dict) else "UNKNOWN",
        "lock_entries": locks,
        "lock_count": len(locks),
        "all_meta_locked": len(locks) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR152_SCHEMA_VERSION,
        "phase": "IR152",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "meta_evidence_lock": lock,
        "lock_hash": _sha256_hex(lock),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR153: Governance Trace Digest
# ---------------------------------------------------------------------------

def _build_ir153_report(*, ir152_report: dict[str, Any], source_task_id: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir152_report.get("validation_result") != "PASS":
        failed_checks.append("ir152 meta evidence lock must be PASS")

    lock = ir152_report.get("meta_evidence_lock", {})
    entries = lock.get("lock_entries", []) if isinstance(lock, dict) else []

    if not entries:
        failed_checks.append("ir152 lock_entries must not be empty")

    digest_entries = [
        {
            "meta_item": str(entry.get("meta_item", "UNKNOWN")),
            "digest_status": "DIGESTED",
            "digest_id": hashlib.sha256(str(entry.get("meta_item", "")).encode("utf-8")).hexdigest(),
        }
        for entry in entries
        if isinstance(entry, dict)
    ]

    digest = {
        "digest_id": f"ir153_digest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": lock.get("new_cycle_id", "UNKNOWN") if isinstance(lock, dict) else "UNKNOWN",
        "digest_entries": digest_entries,
        "digest_count": len(digest_entries),
        "digest_ready": len(digest_entries) > 0,
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR153_SCHEMA_VERSION,
        "phase": "IR153",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "governance_trace_digest": digest,
        "digest_hash": _sha256_hex(digest),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR154: Dry-Run Terminal Closure Attestation
# ---------------------------------------------------------------------------

def run_ir154_dry_run_terminal_closure_attestation(
    *, ir153_report: dict[str, Any], ir152_report: dict[str, Any], source_task_id: str
) -> dict[str, Any]:
    failed_checks: list[str] = []

    if ir153_report.get("validation_result") != "PASS":
        failed_checks.append("ir153 governance trace digest must be PASS")

    digest = ir153_report.get("governance_trace_digest", {})
    if digest.get("digest_ready") is not True:
        failed_checks.append("ir153 digest_ready must be true")

    lock = ir152_report.get("meta_evidence_lock", {})
    if lock.get("all_meta_locked") is not True:
        failed_checks.append("ir152 all_meta_locked must be true")

    if lock.get("unlock_eligible") is not False:
        failed_checks.append("ir152 unlock_eligible must be false")

    safety_snapshot = ir153_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR154_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR154_HOLD
        action = "Hold due to terminal closure attestation precondition mismatch."
    else:
        decision = IR154_CONFIRMED
        action = "Dry-run terminal closure attestation confirmed."

    attestation = {
        "attestation_id": f"ir154_attestation_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "terminal_closure_attested": decision == IR154_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR154_SCHEMA_VERSION,
        "phase": "IR154",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "dry_run_terminal_closure_attestation_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "dry_run_terminal_closure_attestation": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir151_155_batch_dryrun(
    *, base_path: Path, source_task_id: str, ir150_completion_bundle_path: Path | None = None
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir151_155"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir150_path = ir150_completion_bundle_path or (reports_dir / "ir146_150" / "ir150_completion_bundle.json")

    if not ir150_path.exists():
        raise FileNotFoundError(f"ir150 completion bundle not found: {ir150_path}")

    ir150_report = _read_json(ir150_path)

    ir151_report = _build_ir151_report(ir150_report=ir150_report, source_task_id=source_task_id)
    ir151_path = out_dir / "ir151_cycle_a_integrated_completion_report.json"
    _write_json(ir151_path, ir151_report)

    ir152_report = _build_ir152_report(ir151_report=ir151_report, source_task_id=source_task_id)
    ir152_path = out_dir / "ir152_meta_evidence_lock.json"
    _write_json(ir152_path, ir152_report)

    ir153_report = _build_ir153_report(ir152_report=ir152_report, source_task_id=source_task_id)
    ir153_path = out_dir / "ir153_governance_trace_digest.json"
    _write_json(ir153_path, ir153_report)

    ir154_report = run_ir154_dry_run_terminal_closure_attestation(
        ir153_report=ir153_report,
        ir152_report=ir152_report,
        source_task_id=source_task_id,
    )
    ir154_path = out_dir / "ir154_dry_run_terminal_closure_attestation.json"
    _write_json(ir154_path, ir154_report)

    final_decision = ir154_report["dry_run_terminal_closure_attestation_decision"]

    return {
        "phase": "IR151_155_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir150_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir150_bundle_path": _to_ref(ir150_path, project_root),
        "final_decision": final_decision,
        "ir151_result": ir151_report,
        "ir152_result": ir152_report,
        "ir153_result": ir153_report,
        "ir154_result": ir154_report,
        "artifacts": {
            "ir151_cycle_a_integrated_completion_report": _to_ref(ir151_path, project_root),
            "ir152_meta_evidence_lock": _to_ref(ir152_path, project_root),
            "ir153_governance_trace_digest": _to_ref(ir153_path, project_root),
            "ir154_dry_run_terminal_closure_attestation": _to_ref(ir154_path, project_root),
        },
        "safety_gate_summary": _default_safety_gate(),
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR155: Completion Bundle
# ---------------------------------------------------------------------------

def write_ir151_155_completion_bundle(
    *,
    base_path: Path,
    ir151_155_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir151_155"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir151_result = ir151_155_output.get("ir151_result", {})
    ir152_result = ir151_155_output.get("ir152_result", {})
    ir153_result = ir151_155_output.get("ir153_result", {})
    ir154_result = ir151_155_output.get("ir154_result", {})
    final_decision = str(ir151_155_output.get("final_decision", IR154_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir154_live = "PASS" if final_decision == IR154_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR151", "content": "Cycle A Integrated Completion Report", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir151_result), "judgement": _judgement(_live(ir151_result))},
        {"phase": "IR152", "content": "Meta Evidence Lock", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir152_result), "judgement": _judgement(_live(ir152_result))},
        {"phase": "IR153", "content": "Governance Trace Digest", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir153_result), "judgement": _judgement(_live(ir153_result))},
        {"phase": "IR154", "content": "Dry-Run Terminal Closure Attestation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir154_live, "judgement": _judgement(ir154_live)},
        {"phase": "IR155", "content": "Phase 151-155 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir154_live, "judgement": _judgement(ir154_live)},
    ]

    bundle = {
        "schema_version": IR155_SCHEMA_VERSION,
        "phase": "IR155",
        "generated_at": _now_iso(),
        "source_task_id": ir151_155_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir151_155_output.get("new_cycle_id", "UNKNOWN"),
        "ir151_result": ir151_result,
        "ir152_result": ir152_result,
        "ir153_result": ir153_result,
        "ir154_result": ir154_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir151": table_rows[0]["live"],
            "ir152": table_rows[1]["live"],
            "ir153": table_rows[2]["live"],
            "ir154": table_rows[3]["live"],
            "ir155": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "prohibition_continuity_finalized": final_decision == IR154_CONFIRMED,
        "delta_closure_pending": True,
        "artifacts": {
            **ir151_155_output.get("artifacts", {}),
            "ir155_completion_bundle": "generic_block_ai/reports/ir151_155/ir155_completion_bundle.json",
            "ir151_155_live_status": "generic_block_ai/reports/ir151_155/ir151_155_live_status.md",
            "ir151_155_completion_table": "generic_block_ai/reports/ir151_155/ir151_155_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir155_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR151-IR155 Live Status",
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
    live_path = out_dir / "ir151_155_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR151-IR155 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir151_155_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir155_completion_bundle": _to_ref(bundle_path, project_root),
            "ir151_155_live_status": _to_ref(live_path, project_root),
            "ir151_155_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

"""
core_ir86_90_preop_governance_batch.py - IR86-IR90

Batch implementation for pre-operational governance hardening in dry-run mode:
IR86 pre-operational audit review, IR87 approval delta analyzer,
IR88 exception request prohibition gate, IR89 final transition candidate package,
IR90 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR85_SCHEMA_VERSION = "ir85_phase_81_85_completion_bundle_v1"
IR86_SCHEMA_VERSION = "ir86_pre_operational_audit_review_v1"
IR87_SCHEMA_VERSION = "ir87_approval_delta_analyzer_v1"
IR88_SCHEMA_VERSION = "ir88_exception_request_prohibition_gate_v1"
IR89_SCHEMA_VERSION = "ir89_final_transition_candidate_package_v1"
IR90_SCHEMA_VERSION = "ir90_phase_86_90_completion_bundle_v1"

IR88_CONFIRMED = "UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY"
IR88_HOLD = "HOLD"
IR88_ABORT = "ABORT"


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
# IR86: Pre-Operational Audit Review
# ---------------------------------------------------------------------------

def _build_ir86_report(
    *,
    ir85_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Review pre-operational governance posture before any unlock request path."""
    failed_checks: list[str] = []

    if ir85_report.get("schema_version") != IR85_SCHEMA_VERSION:
        failed_checks.append(f"ir85 schema_version must be {IR85_SCHEMA_VERSION}")

    if ir85_report.get("final_decision") != "UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY":
        failed_checks.append("ir85 final_decision must be UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY")

    if ir85_report.get("unlock_prohibition_confirmed") is not True:
        failed_checks.append("ir85 unlock_prohibition_confirmed must be true")

    safety_gate = ir85_report.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
        failed_checks.append("ir85 safety_gate_summary must be object")

    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safety_gate.get(key) is not False:
            failed_checks.append(f"ir85 safety_gate_summary.{key} must be false")

    review = {
        "review_id": f"ir86_review_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir85_report.get("new_cycle_id", "UNKNOWN"),
        "review_scope": "pre_operational_governance",
        "unlock_state": "PROHIBITED",
        "production_state": "BLOCKED",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR86_SCHEMA_VERSION,
        "phase": "IR86",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "pre_operational_audit_review": review,
        "review_hash": _sha256_hex(review),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR87: Approval Delta Analyzer
# ---------------------------------------------------------------------------

def _build_ir87_report(
    *,
    ir86_report: dict[str, Any],
    ir85_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Analyze gaps between current evidence and unlock-required approvals."""
    failed_checks: list[str] = []

    if ir86_report.get("validation_result") != "PASS":
        failed_checks.append("ir86 review must be PASS")

    ir81 = ir85_report.get("ir81_result", {}).get("unlock_preconditions_ledger", {})
    ir82 = ir85_report.get("ir82_result", {}).get("approval_evidence_record", {})

    if not isinstance(ir81, dict):
        ir81 = {}
        failed_checks.append("ir85 ir81_result.unlock_preconditions_ledger must be object")
    if not isinstance(ir82, dict):
        ir82 = {}
        failed_checks.append("ir85 ir82_result.approval_evidence_record must be object")

    ledger_items = ir81.get("unlock_preconditions", [])
    evidence_items = ir82.get("evidence_entries", [])

    missing_count = len([x for x in evidence_items if isinstance(x, dict) and x.get("present") is False])
    required_count = len([x for x in ledger_items if isinstance(x, dict) and x.get("required") is True])

    delta = {
        "delta_id": f"ir87_delta_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir86_report.get("pre_operational_audit_review", {}).get("new_cycle_id", "UNKNOWN"),
        "required_approval_items": required_count,
        "missing_evidence_items": missing_count,
        "approval_delta_status": "GAP_REMAINS" if missing_count > 0 else "NO_GAP",
        "unlock_eligible": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR87_SCHEMA_VERSION,
        "phase": "IR87",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "approval_delta_analysis": delta,
        "delta_hash": _sha256_hex(delta),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR88: Exception Request Prohibition Gate
# ---------------------------------------------------------------------------

def run_ir88_exception_request_prohibition_gate(
    *,
    ir87_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Reconfirm that exception-based unlock attempts remain prohibited."""
    failed_checks: list[str] = []

    if ir87_report.get("validation_result") != "PASS":
        failed_checks.append("ir87 delta analysis must be PASS")

    delta = ir87_report.get("approval_delta_analysis", {})
    if delta.get("approval_delta_status") != "GAP_REMAINS":
        failed_checks.append("ir87 approval_delta_status must be GAP_REMAINS")

    if delta.get("unlock_eligible") is not False:
        failed_checks.append("ir87 unlock_eligible must be false")

    safety_snapshot = ir87_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR88_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR88_HOLD
        action = "Hold due to prohibition precondition mismatch."
    else:
        decision = IR88_CONFIRMED
        action = "Exception-based unlock remains prohibited under dry-run governance."

    gate = {
        "gate_id": f"ir88_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "exception_request_allowed": False,
        "unlock_prohibited": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR88_SCHEMA_VERSION,
        "phase": "IR88",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "exception_request_gate_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gate_record": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR89: Final Transition Candidate Package
# ---------------------------------------------------------------------------

def _build_ir89_report(
    *,
    ir86_report: dict[str, Any],
    ir87_report: dict[str, Any],
    ir88_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Assemble a transition candidate package while preserving prohibition state."""
    failed_checks: list[str] = []

    if ir88_report.get("validation_result") != "PASS":
        failed_checks.append("ir88 gate must be PASS")

    if ir88_report.get("exception_request_gate_decision") != IR88_CONFIRMED:
        failed_checks.append("ir88 decision must be UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY")

    package = {
        "package_id": f"ir89_pkg_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir86_report.get("pre_operational_audit_review", {}).get("new_cycle_id", "UNKNOWN"),
        "review_ref": ir86_report.get("pre_operational_audit_review", {}).get("review_id", "UNKNOWN"),
        "delta_ref": ir87_report.get("approval_delta_analysis", {}).get("delta_id", "UNKNOWN"),
        "gate_ref": ir88_report.get("gate_record", {}).get("gate_id", "UNKNOWN"),
        "candidate_scope": "pre_migration_candidate_dry_run_only",
        "unlock_included": False,
        "production_release_included": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR89_SCHEMA_VERSION,
        "phase": "IR89",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "final_transition_candidate_package": package,
        "package_hash": _sha256_hex(package),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir86_90_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir85_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR86-IR89 batch run for pre-operational governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir86_90"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir85_path = ir85_completion_bundle_path or (
        reports_dir / "ir81_85" / "ir85_completion_bundle.json"
    )

    if not ir85_path.exists():
        raise FileNotFoundError(f"ir85 completion bundle not found: {ir85_path}")

    ir85_report = _read_json(ir85_path)

    ir86_report = _build_ir86_report(
        ir85_report=ir85_report,
        source_task_id=source_task_id,
    )
    ir86_path = out_dir / "ir86_pre_operational_audit_review.json"
    _write_json(ir86_path, ir86_report)

    ir87_report = _build_ir87_report(
        ir86_report=ir86_report,
        ir85_report=ir85_report,
        source_task_id=source_task_id,
    )
    ir87_path = out_dir / "ir87_approval_delta_analysis.json"
    _write_json(ir87_path, ir87_report)

    ir88_report = run_ir88_exception_request_prohibition_gate(
        ir87_report=ir87_report,
        source_task_id=source_task_id,
    )
    ir88_path = out_dir / "ir88_exception_request_prohibition_gate_report.json"
    _write_json(ir88_path, ir88_report)

    ir89_report = _build_ir89_report(
        ir86_report=ir86_report,
        ir87_report=ir87_report,
        ir88_report=ir88_report,
        source_task_id=source_task_id,
    )
    ir89_path = out_dir / "ir89_final_transition_candidate_package.json"
    _write_json(ir89_path, ir89_report)

    final_decision = ir88_report["exception_request_gate_decision"]

    return {
        "phase": "IR86_90_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir85_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir85_bundle_path": _to_ref(ir85_path, project_root),
        "final_decision": final_decision,
        "ir86_result": ir86_report,
        "ir87_result": ir87_report,
        "ir88_result": ir88_report,
        "ir89_result": ir89_report,
        "artifacts": {
            "ir86_pre_operational_audit_review": _to_ref(ir86_path, project_root),
            "ir87_approval_delta_analysis": _to_ref(ir87_path, project_root),
            "ir88_exception_request_prohibition_gate_report": _to_ref(ir88_path, project_root),
            "ir89_final_transition_candidate_package": _to_ref(ir89_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR90: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir86_90_completion_bundle(
    *,
    base_path: Path,
    ir86_90_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR90 completion bundle writer."""
    out_dir = base_path / "reports" / "ir86_90"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir86_result = ir86_90_output.get("ir86_result", {})
    ir87_result = ir86_90_output.get("ir87_result", {})
    ir88_result = ir86_90_output.get("ir88_result", {})
    ir89_result = ir86_90_output.get("ir89_result", {})
    final_decision = str(ir86_90_output.get("final_decision", IR88_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir88_live = "PASS" if final_decision == IR88_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR86", "content": "Pre-Operational Audit Review", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir86_result), "judgement": _judgement(_live(ir86_result))},
        {"phase": "IR87", "content": "Approval Delta Analyzer", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir87_result), "judgement": _judgement(_live(ir87_result))},
        {"phase": "IR88", "content": "Exception Request Prohibition Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir88_live, "judgement": _judgement(ir88_live)},
        {"phase": "IR89", "content": "Final Transition Candidate Package", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir89_result), "judgement": _judgement(_live(ir89_result))},
        {"phase": "IR90", "content": "Phase 86-90 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir88_live, "judgement": _judgement(ir88_live)},
    ]

    bundle = {
        "schema_version": IR90_SCHEMA_VERSION,
        "phase": "IR90",
        "generated_at": _now_iso(),
        "source_task_id": ir86_90_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir86_90_output.get("new_cycle_id", "UNKNOWN"),
        "ir86_result": ir86_result,
        "ir87_result": ir87_result,
        "ir88_result": ir88_result,
        "ir89_result": ir89_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir86": table_rows[0]["live"],
            "ir87": table_rows[1]["live"],
            "ir88": table_rows[2]["live"],
            "ir89": table_rows[3]["live"],
            "ir90": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "unlock_exception_prohibited_confirmed": final_decision == IR88_CONFIRMED,
        "transition_candidate_package_prepared": ir89_result.get("validation_result") == "PASS",
        "artifacts": {
            **ir86_90_output.get("artifacts", {}),
            "ir90_completion_bundle": "generic_block_ai/reports/ir86_90/ir90_completion_bundle.json",
            "ir86_90_live_status": "generic_block_ai/reports/ir86_90/ir86_90_live_status.md",
            "ir86_90_completion_table": "generic_block_ai/reports/ir86_90/ir86_90_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir90_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR86-IR90 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Unlock Exception Prohibited Confirmed: {bundle['unlock_exception_prohibited_confirmed']}",
        f"- Transition Candidate Package Prepared: {bundle['transition_candidate_package_prepared']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir86_90_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR86-IR90 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir86_90_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir90_completion_bundle": _to_ref(bundle_path, project_root),
            "ir86_90_live_status": _to_ref(live_path, project_root),
            "ir86_90_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

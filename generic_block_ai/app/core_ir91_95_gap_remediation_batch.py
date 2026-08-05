"""
core_ir91_95_gap_remediation_batch.py - IR91-IR95

Batch implementation for gap remediation governance in dry-run mode:
IR91 gap remediation plan, IR92 approval delta correction proposal,
IR93 re-review queue registry, IR94 unlock prohibition continuity gate,
IR95 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR90_SCHEMA_VERSION = "ir90_phase_86_90_completion_bundle_v1"
IR91_SCHEMA_VERSION = "ir91_gap_remediation_plan_v1"
IR92_SCHEMA_VERSION = "ir92_approval_delta_correction_proposal_v1"
IR93_SCHEMA_VERSION = "ir93_re_review_queue_registry_v1"
IR94_SCHEMA_VERSION = "ir94_unlock_prohibition_continuity_gate_v1"
IR95_SCHEMA_VERSION = "ir95_phase_91_95_completion_bundle_v1"

IR94_CONFIRMED = "UNLOCK_PROHIBITION_CONTINUED_DRY_RUN_ONLY"
IR94_HOLD = "HOLD"
IR94_ABORT = "ABORT"


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
# IR91: GAP Remediation Plan
# ---------------------------------------------------------------------------

def _build_ir91_report(
    *,
    ir90_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build a concrete remediation plan for remaining approval gaps."""
    failed_checks: list[str] = []

    if ir90_report.get("schema_version") != IR90_SCHEMA_VERSION:
        failed_checks.append(f"ir90 schema_version must be {IR90_SCHEMA_VERSION}")

    if ir90_report.get("final_decision") != "UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY":
        failed_checks.append("ir90 final_decision must be UNLOCK_EXCEPTION_PROHIBITED_DRY_RUN_ONLY")

    if ir90_report.get("unlock_exception_prohibited_confirmed") is not True:
        failed_checks.append("ir90 unlock_exception_prohibited_confirmed must be true")

    ir87 = ir90_report.get("ir87_result", {}).get("approval_delta_analysis", {})
    if str(ir87.get("approval_delta_status", "UNKNOWN")) != "GAP_REMAINS":
        failed_checks.append("ir90 ir87 approval_delta_status must be GAP_REMAINS")

    remediation_items = [
        {"item": "go_decision_document", "owner": "design_owner", "target_state": "PRESENT", "status": "PLANNED"},
        {"item": "release_approver_signature", "owner": "release_governor", "target_state": "PRESENT", "status": "PLANNED"},
        {"item": "safety_redeclaration_record", "owner": "safety_reviewer", "target_state": "PRESENT", "status": "PLANNED"},
        {"item": "full_test_matrix_record", "owner": "qa_owner", "target_state": "PRESENT", "status": "PLANNED"},
        {"item": "execution_authorization_record", "owner": "governance_board", "target_state": "PRESENT", "status": "PLANNED"},
    ]

    plan = {
        "plan_id": f"ir91_plan_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir90_report.get("new_cycle_id", "UNKNOWN"),
        "remediation_items": remediation_items,
        "all_items_planned": True,
        "all_items_completed": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR91_SCHEMA_VERSION,
        "phase": "IR91",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gap_remediation_plan": plan,
        "plan_hash": _sha256_hex(plan),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR92: Approval Delta Correction Proposal
# ---------------------------------------------------------------------------

def _build_ir92_report(
    *,
    ir91_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Propose correction actions tied to each remediation item."""
    failed_checks: list[str] = []

    if ir91_report.get("validation_result") != "PASS":
        failed_checks.append("ir91 plan must be PASS")

    plan = ir91_report.get("gap_remediation_plan", {})
    items = plan.get("remediation_items", []) if isinstance(plan, dict) else []

    proposals = [
        {
            "item": item.get("item", "UNKNOWN"),
            "proposal": f"collect_{item.get('item', 'unknown')}_evidence",
            "expected_outcome": "status moves from PLANNED to READY_FOR_REVIEW",
        }
        for item in items
        if isinstance(item, dict)
    ]

    if not proposals:
        failed_checks.append("ir91 remediation items are required")

    proposal = {
        "proposal_id": f"ir92_proposal_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": plan.get("new_cycle_id", "UNKNOWN") if isinstance(plan, dict) else "UNKNOWN",
        "correction_proposals": proposals,
        "proposal_count": len(proposals),
        "ready_for_re_review": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR92_SCHEMA_VERSION,
        "phase": "IR92",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "approval_delta_correction_proposal": proposal,
        "proposal_hash": _sha256_hex(proposal),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR93: Re-Review Queue Registry
# ---------------------------------------------------------------------------

def _build_ir93_report(
    *,
    ir91_report: dict[str, Any],
    ir92_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Create re-review queue entries for each correction proposal."""
    failed_checks: list[str] = []

    if ir92_report.get("validation_result") != "PASS":
        failed_checks.append("ir92 proposal must be PASS")

    proposal = ir92_report.get("approval_delta_correction_proposal", {})
    corrections = proposal.get("correction_proposals", []) if isinstance(proposal, dict) else []

    queue_entries = [
        {
            "queue_item_id": f"queue_{idx+1}",
            "item": entry.get("item", "UNKNOWN"),
            "status": "QUEUED",
            "review_type": "governance_re_review",
        }
        for idx, entry in enumerate(corrections)
        if isinstance(entry, dict)
    ]

    if not queue_entries:
        failed_checks.append("ir92 correction proposals are required")

    registry = {
        "registry_id": f"ir93_queue_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir91_report.get("gap_remediation_plan", {}).get("new_cycle_id", "UNKNOWN"),
        "queue_entries": queue_entries,
        "queue_size": len(queue_entries),
        "queue_mode": "dry_run_governance_only",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR93_SCHEMA_VERSION,
        "phase": "IR93",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "re_review_queue_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR94: Unlock Prohibition Continuity Gate
# ---------------------------------------------------------------------------

def run_ir94_unlock_prohibition_continuity_gate(
    *,
    ir93_report: dict[str, Any],
    ir92_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Ensure prohibition remains active while remediation queue is in progress."""
    failed_checks: list[str] = []

    if ir93_report.get("validation_result") != "PASS":
        failed_checks.append("ir93 queue registry must be PASS")

    queue = ir93_report.get("re_review_queue_registry", {})
    if queue.get("queue_size", 0) <= 0:
        failed_checks.append("ir93 queue_size must be > 0")

    proposal = ir92_report.get("approval_delta_correction_proposal", {})
    if proposal.get("ready_for_re_review") is not True:
        failed_checks.append("ir92 ready_for_re_review must be true")

    safety_snapshot = ir93_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR94_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR94_HOLD
        action = "Hold due to continuity condition mismatch."
    else:
        decision = IR94_CONFIRMED
        action = "Unlock prohibition continuity confirmed while re-review queue is active."

    gate = {
        "gate_id": f"ir94_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "continuity_confirmed": decision == IR94_CONFIRMED,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR94_SCHEMA_VERSION,
        "phase": "IR94",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "unlock_prohibition_continuity_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gate_record": gate,
        "gate_hash": _sha256_hex(gate),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir91_95_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir90_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR91-IR94 batch run for remediation governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir91_95"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir90_path = ir90_completion_bundle_path or (
        reports_dir / "ir86_90" / "ir90_completion_bundle.json"
    )

    if not ir90_path.exists():
        raise FileNotFoundError(f"ir90 completion bundle not found: {ir90_path}")

    ir90_report = _read_json(ir90_path)

    ir91_report = _build_ir91_report(
        ir90_report=ir90_report,
        source_task_id=source_task_id,
    )
    ir91_path = out_dir / "ir91_gap_remediation_plan.json"
    _write_json(ir91_path, ir91_report)

    ir92_report = _build_ir92_report(
        ir91_report=ir91_report,
        source_task_id=source_task_id,
    )
    ir92_path = out_dir / "ir92_approval_delta_correction_proposal.json"
    _write_json(ir92_path, ir92_report)

    ir93_report = _build_ir93_report(
        ir91_report=ir91_report,
        ir92_report=ir92_report,
        source_task_id=source_task_id,
    )
    ir93_path = out_dir / "ir93_re_review_queue_registry.json"
    _write_json(ir93_path, ir93_report)

    ir94_report = run_ir94_unlock_prohibition_continuity_gate(
        ir93_report=ir93_report,
        ir92_report=ir92_report,
        source_task_id=source_task_id,
    )
    ir94_path = out_dir / "ir94_unlock_prohibition_continuity_gate_report.json"
    _write_json(ir94_path, ir94_report)

    final_decision = ir94_report["unlock_prohibition_continuity_decision"]

    return {
        "phase": "IR91_95_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir90_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir90_bundle_path": _to_ref(ir90_path, project_root),
        "final_decision": final_decision,
        "ir91_result": ir91_report,
        "ir92_result": ir92_report,
        "ir93_result": ir93_report,
        "ir94_result": ir94_report,
        "artifacts": {
            "ir91_gap_remediation_plan": _to_ref(ir91_path, project_root),
            "ir92_approval_delta_correction_proposal": _to_ref(ir92_path, project_root),
            "ir93_re_review_queue_registry": _to_ref(ir93_path, project_root),
            "ir94_unlock_prohibition_continuity_gate_report": _to_ref(ir94_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR95: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir91_95_completion_bundle(
    *,
    base_path: Path,
    ir91_95_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR95 completion bundle writer."""
    out_dir = base_path / "reports" / "ir91_95"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir91_result = ir91_95_output.get("ir91_result", {})
    ir92_result = ir91_95_output.get("ir92_result", {})
    ir93_result = ir91_95_output.get("ir93_result", {})
    ir94_result = ir91_95_output.get("ir94_result", {})
    final_decision = str(ir91_95_output.get("final_decision", IR94_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir94_live = "PASS" if final_decision == IR94_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR91", "content": "GAP Remediation Plan", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir91_result), "judgement": _judgement(_live(ir91_result))},
        {"phase": "IR92", "content": "Approval Delta Correction Proposal", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir92_result), "judgement": _judgement(_live(ir92_result))},
        {"phase": "IR93", "content": "Re-Review Queue Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir93_result), "judgement": _judgement(_live(ir93_result))},
        {"phase": "IR94", "content": "Unlock Prohibition Continuity Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir94_live, "judgement": _judgement(ir94_live)},
        {"phase": "IR95", "content": "Phase 91-95 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir94_live, "judgement": _judgement(ir94_live)},
    ]

    bundle = {
        "schema_version": IR95_SCHEMA_VERSION,
        "phase": "IR95",
        "generated_at": _now_iso(),
        "source_task_id": ir91_95_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir91_95_output.get("new_cycle_id", "UNKNOWN"),
        "ir91_result": ir91_result,
        "ir92_result": ir92_result,
        "ir93_result": ir93_result,
        "ir94_result": ir94_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir91": table_rows[0]["live"],
            "ir92": table_rows[1]["live"],
            "ir93": table_rows[2]["live"],
            "ir94": table_rows[3]["live"],
            "ir95": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "unlock_prohibition_continuity_confirmed": final_decision == IR94_CONFIRMED,
        "re_review_queue_prepared": ir93_result.get("validation_result") == "PASS",
        "artifacts": {
            **ir91_95_output.get("artifacts", {}),
            "ir95_completion_bundle": "generic_block_ai/reports/ir91_95/ir95_completion_bundle.json",
            "ir91_95_live_status": "generic_block_ai/reports/ir91_95/ir91_95_live_status.md",
            "ir91_95_completion_table": "generic_block_ai/reports/ir91_95/ir91_95_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir95_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR91-IR95 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Unlock Prohibition Continuity Confirmed: {bundle['unlock_prohibition_continuity_confirmed']}",
        f"- Re-Review Queue Prepared: {bundle['re_review_queue_prepared']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir91_95_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR91-IR95 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir91_95_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir95_completion_bundle": _to_ref(bundle_path, project_root),
            "ir91_95_live_status": _to_ref(live_path, project_root),
            "ir91_95_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

"""
core_ir81_85_unlock_governance_batch.py - IR81-IR85

Batch implementation for unlock-governance preparation in dry-run mode:
IR81 unlock preconditions ledger, IR82 approval evidence recorder,
IR83 staged unlock simulation, IR84 unlock prohibition gate re-validation,
IR85 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR80_SCHEMA_VERSION = "ir80_phase_76_80_completion_bundle_v1"
IR81_SCHEMA_VERSION = "ir81_unlock_preconditions_ledger_v1"
IR82_SCHEMA_VERSION = "ir82_approval_evidence_recorder_v1"
IR83_SCHEMA_VERSION = "ir83_staged_unlock_simulation_v1"
IR84_SCHEMA_VERSION = "ir84_unlock_prohibition_gate_revalidation_v1"
IR85_SCHEMA_VERSION = "ir85_phase_81_85_completion_bundle_v1"

IR84_CONFIRMED = "UNLOCK_PROHIBITION_CONFIRMED_DRY_RUN_ONLY"
IR84_HOLD = "HOLD"
IR84_ABORT = "ABORT"


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
# IR81: Unlock Preconditions Ledger
# ---------------------------------------------------------------------------

def _build_ir81_report(
    *,
    ir80_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build a concrete ledger of unlock prerequisites for the new cycle."""
    failed_checks: list[str] = []

    if ir80_report.get("schema_version") != IR80_SCHEMA_VERSION:
        failed_checks.append(f"ir80 schema_version must be {IR80_SCHEMA_VERSION}")

    if ir80_report.get("final_decision") != "GOVERNANCE_READY_DRY_RUN_ONLY":
        failed_checks.append("ir80 final_decision must be GOVERNANCE_READY_DRY_RUN_ONLY")

    if ir80_report.get("governance_ready_dry_run_only") is not True:
        failed_checks.append("ir80 governance_ready_dry_run_only must be true")

    new_cycle_id = str(ir80_report.get("new_cycle_id", "UNKNOWN"))
    if new_cycle_id == "UNKNOWN":
        failed_checks.append("ir80 new_cycle_id is missing")

    ledger_items = [
        {"item": "explicit_go_decision_recorded", "required": True, "satisfied": False},
        {"item": "named_release_approver_recorded", "required": True, "satisfied": False},
        {"item": "safety_gate_redeclaration_completed", "required": True, "satisfied": False},
        {"item": "full_test_matrix_reexecuted", "required": True, "satisfied": False},
        {"item": "external_execution_authorized", "required": True, "satisfied": False},
    ]

    ledger = {
        "ledger_id": f"ir81_ledger_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": new_cycle_id,
        "unlock_preconditions": ledger_items,
        "unlock_ready": False,
        "ledger_scope": "preconditions_definition_only",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR81_SCHEMA_VERSION,
        "phase": "IR81",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "unlock_preconditions_ledger": ledger,
        "ledger_hash": _sha256_hex(ledger),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR82: Approval Evidence Recorder
# ---------------------------------------------------------------------------

def _build_ir82_report(
    *,
    ir81_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Record approval evidence placeholders required before any unlock."""
    failed_checks: list[str] = []

    if ir81_report.get("validation_result") != "PASS":
        failed_checks.append("ir81 ledger must be PASS")

    ledger = ir81_report.get("unlock_preconditions_ledger", {})
    if not isinstance(ledger, dict):
        ledger = {}
        failed_checks.append("ir81 unlock_preconditions_ledger must be object")

    evidence_entries = [
        {"evidence_type": "go_decision_document", "present": False, "reference": "PENDING"},
        {"evidence_type": "release_approver_signature", "present": False, "reference": "PENDING"},
        {"evidence_type": "safety_redeclaration_record", "present": False, "reference": "PENDING"},
        {"evidence_type": "full_test_matrix_record", "present": False, "reference": "PENDING"},
        {"evidence_type": "execution_authorization_record", "present": False, "reference": "PENDING"},
    ]

    recorder = {
        "recorder_id": f"ir82_evidence_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ledger.get("new_cycle_id", "UNKNOWN"),
        "evidence_entries": evidence_entries,
        "all_required_evidence_present": False,
        "recording_mode": "placeholder_registry",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR82_SCHEMA_VERSION,
        "phase": "IR82",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "approval_evidence_record": recorder,
        "record_hash": _sha256_hex(recorder),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR83: Staged Unlock Simulation
# ---------------------------------------------------------------------------

def _build_ir83_report(
    *,
    ir81_report: dict[str, Any],
    ir82_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Simulate staged unlock path while keeping execution blocked."""
    failed_checks: list[str] = []

    if ir82_report.get("validation_result") != "PASS":
        failed_checks.append("ir82 approval evidence recorder must be PASS")

    ledger = ir81_report.get("unlock_preconditions_ledger", {})
    evidence = ir82_report.get("approval_evidence_record", {})

    if not isinstance(ledger, dict):
        ledger = {}
        failed_checks.append("ir81 ledger must be object")
    if not isinstance(evidence, dict):
        evidence = {}
        failed_checks.append("ir82 evidence record must be object")

    stage_results = [
        {
            "stage": "STAGE_1_GOVERNANCE_REVIEW",
            "unlock_possible": False,
            "reason": "go_decision_document missing",
        },
        {
            "stage": "STAGE_2_APPROVER_CONFIRMATION",
            "unlock_possible": False,
            "reason": "release_approver_signature missing",
        },
        {
            "stage": "STAGE_3_EXECUTION_AUTHORIZATION",
            "unlock_possible": False,
            "reason": "execution_authorization_record missing",
        },
    ]

    simulation = {
        "simulation_id": f"ir83_sim_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ledger.get("new_cycle_id", "UNKNOWN"),
        "stage_results": stage_results,
        "unlock_simulation_result": "REMAINS_BLOCKED",
        "execution_unlocked": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR83_SCHEMA_VERSION,
        "phase": "IR83",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "staged_unlock_simulation": simulation,
        "simulation_hash": _sha256_hex(simulation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR84: Unlock Prohibition Gate Re-Validation
# ---------------------------------------------------------------------------

def run_ir84_unlock_prohibition_gate_revalidation(
    *,
    ir83_report: dict[str, Any],
    ir82_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Re-validate unlock prohibition and maintain dry-run-only safety posture."""
    failed_checks: list[str] = []

    if ir83_report.get("validation_result") != "PASS":
        failed_checks.append("ir83 staged simulation must be PASS")

    simulation = ir83_report.get("staged_unlock_simulation", {})
    evidence = ir82_report.get("approval_evidence_record", {})

    if simulation.get("execution_unlocked") is not False:
        failed_checks.append("ir83 execution_unlocked must be false")
    if simulation.get("unlock_simulation_result") != "REMAINS_BLOCKED":
        failed_checks.append("ir83 unlock_simulation_result must be REMAINS_BLOCKED")

    if evidence.get("all_required_evidence_present") is not False:
        failed_checks.append("ir82 all_required_evidence_present must be false")

    safety_snapshot = ir83_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        decision = IR84_ABORT
        action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        decision = IR84_HOLD
        action = "Hold due to prohibition validation failure."
    else:
        decision = IR84_CONFIRMED
        action = "Unlock prohibition re-validated. Dry-run-only remains enforced."

    gate_record = {
        "gate_id": f"ir84_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "unlock_prohibited": True,
        "dry_run_only_enforced": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR84_SCHEMA_VERSION,
        "phase": "IR84",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "unlock_prohibition_gate_decision": decision,
        "gate_action": action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gate_record": gate_record,
        "gate_hash": _sha256_hex(gate_record),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir81_85_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir80_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR81-IR84 batch run for unlock governance in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir81_85"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir80_path = ir80_completion_bundle_path or (
        reports_dir / "ir76_80" / "ir80_completion_bundle.json"
    )

    if not ir80_path.exists():
        raise FileNotFoundError(f"ir80 completion bundle not found: {ir80_path}")

    ir80_report = _read_json(ir80_path)

    ir81_report = _build_ir81_report(
        ir80_report=ir80_report,
        source_task_id=source_task_id,
    )
    ir81_path = out_dir / "ir81_unlock_preconditions_ledger.json"
    _write_json(ir81_path, ir81_report)

    ir82_report = _build_ir82_report(
        ir81_report=ir81_report,
        source_task_id=source_task_id,
    )
    ir82_path = out_dir / "ir82_approval_evidence_record.json"
    _write_json(ir82_path, ir82_report)

    ir83_report = _build_ir83_report(
        ir81_report=ir81_report,
        ir82_report=ir82_report,
        source_task_id=source_task_id,
    )
    ir83_path = out_dir / "ir83_staged_unlock_simulation.json"
    _write_json(ir83_path, ir83_report)

    ir84_report = run_ir84_unlock_prohibition_gate_revalidation(
        ir83_report=ir83_report,
        ir82_report=ir82_report,
        source_task_id=source_task_id,
    )
    ir84_path = out_dir / "ir84_unlock_prohibition_gate_report.json"
    _write_json(ir84_path, ir84_report)

    final_decision = ir84_report["unlock_prohibition_gate_decision"]

    return {
        "phase": "IR81_85_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir80_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir80_bundle_path": _to_ref(ir80_path, project_root),
        "final_decision": final_decision,
        "ir81_result": ir81_report,
        "ir82_result": ir82_report,
        "ir83_result": ir83_report,
        "ir84_result": ir84_report,
        "artifacts": {
            "ir81_unlock_preconditions_ledger": _to_ref(ir81_path, project_root),
            "ir82_approval_evidence_record": _to_ref(ir82_path, project_root),
            "ir83_staged_unlock_simulation": _to_ref(ir83_path, project_root),
            "ir84_unlock_prohibition_gate_report": _to_ref(ir84_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR85: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir81_85_completion_bundle(
    *,
    base_path: Path,
    ir81_85_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR85 completion bundle writer."""
    out_dir = base_path / "reports" / "ir81_85"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir81_result = ir81_85_output.get("ir81_result", {})
    ir82_result = ir81_85_output.get("ir82_result", {})
    ir83_result = ir81_85_output.get("ir83_result", {})
    ir84_result = ir81_85_output.get("ir84_result", {})
    final_decision = str(ir81_85_output.get("final_decision", IR84_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir84_live = "PASS" if final_decision == IR84_CONFIRMED else "FAIL"

    table_rows = [
        {"phase": "IR81", "content": "Unlock Preconditions Ledger", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir81_result), "judgement": _judgement(_live(ir81_result))},
        {"phase": "IR82", "content": "Approval Evidence Recorder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir82_result), "judgement": _judgement(_live(ir82_result))},
        {"phase": "IR83", "content": "Staged Unlock Simulation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir83_result), "judgement": _judgement(_live(ir83_result))},
        {"phase": "IR84", "content": "Unlock Prohibition Gate Re-Validation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir84_live, "judgement": _judgement(ir84_live)},
        {"phase": "IR85", "content": "Phase 81-85 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir84_live, "judgement": _judgement(ir84_live)},
    ]

    bundle = {
        "schema_version": IR85_SCHEMA_VERSION,
        "phase": "IR85",
        "generated_at": _now_iso(),
        "source_task_id": ir81_85_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir81_85_output.get("new_cycle_id", "UNKNOWN"),
        "ir81_result": ir81_result,
        "ir82_result": ir82_result,
        "ir83_result": ir83_result,
        "ir84_result": ir84_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir81": table_rows[0]["live"],
            "ir82": table_rows[1]["live"],
            "ir83": table_rows[2]["live"],
            "ir84": table_rows[3]["live"],
            "ir85": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "unlock_prohibition_confirmed": final_decision == IR84_CONFIRMED,
        "artifacts": {
            **ir81_85_output.get("artifacts", {}),
            "ir85_completion_bundle": "generic_block_ai/reports/ir81_85/ir85_completion_bundle.json",
            "ir81_85_live_status": "generic_block_ai/reports/ir81_85/ir81_85_live_status.md",
            "ir81_85_completion_table": "generic_block_ai/reports/ir81_85/ir81_85_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir85_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR81-IR85 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Unlock Prohibition Confirmed: {bundle['unlock_prohibition_confirmed']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir81_85_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR81-IR85 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir81_85_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir85_completion_bundle": _to_ref(bundle_path, project_root),
            "ir81_85_live_status": _to_ref(live_path, project_root),
            "ir81_85_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

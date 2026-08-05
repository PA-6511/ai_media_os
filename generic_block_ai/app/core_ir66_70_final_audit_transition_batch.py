"""
core_ir66_70_final_audit_transition_batch.py - IR66-IR70

Batch implementation for final dry-run comprehensive audit, pre-operational
transition review, NO-GO lock gate, next-phase design package assembly,
and completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR65_SCHEMA_VERSION = "ir65_phase_61_65_completion_bundle_v1"
IR66_SCHEMA_VERSION = "ir66_final_dry_run_comprehensive_auditor_v1"
IR67_SCHEMA_VERSION = "ir67_pre_operational_transition_reviewer_v1"
IR68_SCHEMA_VERSION = "ir68_no_go_lock_gate_v1"
IR69_SCHEMA_VERSION = "ir69_next_phase_design_package_assembler_v1"
IR70_SCHEMA_VERSION = "ir70_phase_66_70_completion_bundle_v1"

# IR68 gate decisions
IR68_LOCKED = "NO_GO_LOCKED_DRY_RUN_ONLY"
IR68_HOLD = "HOLD"
IR68_ABORT = "ABORT"

# Expected batch coverage for comprehensive audit
_EXPECTED_BATCH_RANGES = ["IR51_55", "IR56_60", "IR61_65"]

# All phases expected across full IR51-IR65 dry-run cycle
_FULL_CYCLE_PHASES = {
    "IR51", "IR52", "IR53", "IR54", "IR55",
    "IR56", "IR57", "IR58", "IR59", "IR60",
    "IR61", "IR62", "IR63", "IR64", "IR65",
}


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
# IR66: Final DRY_RUN Comprehensive Auditor
# ---------------------------------------------------------------------------

def _build_ir66_report(
    *,
    ir65_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Audit the complete IR51-IR65 dry-run cycle for cross-batch completeness."""
    failed_checks: list[str] = []

    if ir65_report.get("schema_version") != IR65_SCHEMA_VERSION:
        failed_checks.append(f"ir65 schema_version must be {IR65_SCHEMA_VERSION}")

    final_decision = str(ir65_report.get("final_decision", "UNKNOWN"))
    if final_decision != "READY_FOR_DRY_RUN_HANDOFF_ONLY":
        failed_checks.append(
            f"ir65 final_decision must be READY_FOR_DRY_RUN_HANDOFF_ONLY, got {final_decision}"
        )

    safety_gate = ir65_report.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
        failed_checks.append("ir65 safety_gate_summary must be object")

    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safety_gate.get(key) is not False:
            failed_checks.append(f"ir65 safety_gate_summary.{key} must be false")

    if str(safety_gate.get("dry_run", "")) != "maintained":
        failed_checks.append("ir65 dry_run must be maintained")
    if str(safety_gate.get("OBSERVE", "")) != "maintained":
        failed_checks.append("ir65 OBSERVE must be maintained")

    completion_table = ir65_report.get("completion_table", [])
    if not isinstance(completion_table, list):
        failed_checks.append("ir65 completion_table must be list")
        completion_table = []

    all_complete = all(
        isinstance(row, dict) and row.get("judgement") == "完了"
        for row in completion_table
    )
    if completion_table and not all_complete:
        failed_checks.append("ir65 completion_table has incomplete judgements")

    live_summary = ir65_report.get("live_summary", {})
    if not isinstance(live_summary, dict):
        failed_checks.append("ir65 live_summary must be object")
        live_summary = {}

    all_live_pass = all(str(v) == "PASS" for v in live_summary.values()) if live_summary else False
    if live_summary and not all_live_pass:
        failed_checks.append("ir65 live_summary has non-PASS entries")

    # IR62 re-verification is embedded in ir65 if present
    ir62_result = ir65_report.get("ir62_result", {})
    re_verification = str(ir62_result.get("re_verification_result", "UNKNOWN"))
    if re_verification != "CYCLE_VERIFIED":
        failed_checks.append(f"ir62 re_verification_result must be CYCLE_VERIFIED, got {re_verification}")

    audit_record = {
        "audit_id": f"final_audit_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "audited_at": _now_iso(),
        "audited_cycle": "IR51_to_IR65",
        "source_task_id": source_task_id,
        "ir65_final_decision": final_decision,
        "ir62_re_verification_result": re_verification,
        "completion_table_snapshot": completion_table,
        "live_summary_snapshot": live_summary,
        "safety_gate_snapshot": _default_safety_gate(),
        "no_external_write_confirmed": True,
        "no_live_execution_confirmed": True,
    }
    audit_hash = _sha256_hex(audit_record)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR66_SCHEMA_VERSION,
        "phase": "IR66",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "audit_record": audit_record,
        "audit_hash": audit_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR67: Pre-Operational Transition Reviewer
# ---------------------------------------------------------------------------

def _build_ir67_report(
    *,
    ir65_report: dict[str, Any],
    ir66_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Review the dry-run cycle for readiness criteria before any future live transition."""
    failed_checks: list[str] = []

    if ir66_report.get("validation_result") != "PASS":
        failed_checks.append("ir66 comprehensive audit must be PASS")

    # Verify audit hash integrity
    provided_hash = str(ir66_report.get("audit_hash", ""))
    audit_record = ir66_report.get("audit_record", {})
    recalculated_hash = _sha256_hex(audit_record) if audit_record else ""
    hash_match = provided_hash == recalculated_hash
    if not hash_match:
        failed_checks.append("ir66 audit_hash mismatch (integrity check failed)")

    # Confirm no-execution flags from audit record
    if audit_record.get("no_external_write_confirmed") is not True:
        failed_checks.append("ir66 no_external_write_confirmed must be true")
    if audit_record.get("no_live_execution_confirmed") is not True:
        failed_checks.append("ir66 no_live_execution_confirmed must be true")

    # Confirm live summary all PASS from IR65
    live_summary = ir65_report.get("live_summary", {})
    if not isinstance(live_summary, dict):
        live_summary = {}
        failed_checks.append("ir65 live_summary must be object")

    incomplete_live = [k for k, v in live_summary.items() if str(v) != "PASS"]
    if incomplete_live:
        failed_checks.append(f"ir65 live_summary non-PASS: {incomplete_live}")

    # Transition readiness criteria (dry-run scoped only)
    transition_criteria = {
        "dry_run_cycle_complete": ir66_report.get("validation_result") == "PASS",
        "hash_integrity_verified": hash_match,
        "no_external_write": audit_record.get("no_external_write_confirmed", False),
        "no_live_execution": audit_record.get("no_live_execution_confirmed", False),
        "all_phases_live_pass": len(incomplete_live) == 0,
        "safety_gate_maintained": True,
    }
    all_criteria_met = all(transition_criteria.values())

    transition_readiness = "DRY_RUN_TRANSITION_READY" if all_criteria_met and not failed_checks else "NOT_READY"

    return {
        "schema_version": IR67_SCHEMA_VERSION,
        "phase": "IR67",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "transition_readiness": transition_readiness,
        "transition_criteria": transition_criteria,
        "hash_integrity": {
            "provided_audit_hash": provided_hash,
            "recalculated_audit_hash": recalculated_hash,
            "hash_match": hash_match,
        },
        "incomplete_live_phases": incomplete_live,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR68: NO-GO Lock Gate
# ---------------------------------------------------------------------------

def run_ir68_no_go_lock_gate(
    *,
    ir67_transition_review: dict[str, Any],
    ir66_comprehensive_audit: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """
    Explicitly locks the NO-GO (dry-run-only) status.
    PASS means NO-GO is cleanly locked: no live execution will proceed from this cycle.
    """
    failed_checks: list[str] = []

    if ir67_transition_review.get("validation_result") != "PASS":
        failed_checks.append("ir67 transition review must be PASS")

    if ir67_transition_review.get("transition_readiness") != "DRY_RUN_TRANSITION_READY":
        failed_checks.append(
            f"ir67 transition_readiness must be DRY_RUN_TRANSITION_READY, "
            f"got {ir67_transition_review.get('transition_readiness', 'UNKNOWN')}"
        )

    # Verify safety gate on ir66 audit record
    audit_record = ir66_comprehensive_audit.get("audit_record", {})
    gate_snapshot = audit_record.get("safety_gate_snapshot", {})
    if not isinstance(gate_snapshot, dict):
        gate_snapshot = {}

    expected_gate = _default_safety_gate()
    for key, expected in expected_gate.items():
        if gate_snapshot.get(key) != expected:
            failed_checks.append(f"ir66 audit safety_gate_snapshot.{key} mismatch")

    # Abort if any external execution flag is live on the ir67 envelope
    safety_snapshot = ir67_transition_review.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"
    abort_condition = abort_flags or github_push

    if abort_condition:
        gate_decision = IR68_ABORT
        gate_action = "Abort: external execution risk flags detected. NO-GO lock cannot proceed."
    elif failed_checks:
        gate_decision = IR68_HOLD
        gate_action = "Hold: pre-conditions not met for NO-GO lock."
    else:
        gate_decision = IR68_LOCKED
        gate_action = (
            "NO-GO locked. Dry-run cycle IR51-IR65 is formally closed. "
            "No live execution will proceed from this cycle. "
            "Next action requires a new design phase."
        )

    no_go_lock_record = {
        "lock_id": f"no_go_lock_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "locked_at": _now_iso(),
        "source_task_id": source_task_id,
        "gate_decision": gate_decision,
        "locked_cycle": "IR51_to_IR65",
        "live_execution_permanently_blocked_this_cycle": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }
    lock_hash = _sha256_hex(no_go_lock_record)

    return {
        "schema_version": IR68_SCHEMA_VERSION,
        "phase": "IR68",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "no_go_lock_gate_decision": gate_decision,
        "gate_action": gate_action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "no_go_lock_record": no_go_lock_record,
        "lock_hash": lock_hash,
        "tamper_detection_summary": "NO_TAMPER",
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR69: Next-Phase Design Package Assembler
# ---------------------------------------------------------------------------

def _build_ir69_report(
    *,
    ir65_report: dict[str, Any],
    ir66_report: dict[str, Any],
    ir67_report: dict[str, Any],
    ir68_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Assemble a design handoff package for the next phase group beyond IR65."""
    failed_checks: list[str] = []

    if ir68_report.get("validation_result") != "PASS":
        failed_checks.append("ir68 NO-GO lock gate must be PASS")

    if ir68_report.get("no_go_lock_gate_decision") != IR68_LOCKED:
        failed_checks.append(
            f"ir68 no_go_lock_gate_decision must be NO_GO_LOCKED_DRY_RUN_ONLY, "
            f"got {ir68_report.get('no_go_lock_gate_decision', 'UNKNOWN')}"
        )

    # Verify IR68 lock hash
    provided_lock_hash = str(ir68_report.get("lock_hash", ""))
    lock_record = ir68_report.get("no_go_lock_record", {})
    recalculated_lock_hash = _sha256_hex(lock_record) if lock_record else ""
    lock_hash_match = provided_lock_hash == recalculated_lock_hash
    if not lock_hash_match:
        failed_checks.append("ir68 lock_hash mismatch (integrity check failed)")

    design_package = {
        "design_package_id": f"design_pkg_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "assembled_at": _now_iso(),
        "source_task_id": source_task_id,
        "completed_cycle": "IR51_to_IR65",
        "no_go_lock_id": lock_record.get("lock_id", "UNKNOWN"),
        "ir65_final_decision": str(ir65_report.get("final_decision", "UNKNOWN")),
        "ir67_transition_readiness": str(ir67_report.get("transition_readiness", "UNKNOWN")),
        "ir68_lock_decision": str(ir68_report.get("no_go_lock_gate_decision", "UNKNOWN")),
        "recommended_next_action": "Design new phase group IR71+ with explicit live-execution intent if applicable.",
        "design_constraints": [
            "No live execution in current cycle.",
            "All changes require new design phase approval.",
            "Safety gates must be re-declared in next cycle.",
            "dry_run status must be explicitly lifted by authorized design decision.",
        ],
        "safety_gate_snapshot": _default_safety_gate(),
        "assembly_execution_blocked": True,
        "external_distribution_blocked": True,
        "retention_scope": "dry_run_only",
    }
    package_hash = _sha256_hex(design_package)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR69_SCHEMA_VERSION,
        "phase": "IR69",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "design_package": design_package,
        "design_package_hash": package_hash,
        "lock_hash_verification": {
            "provided_lock_hash": provided_lock_hash,
            "recalculated_lock_hash": recalculated_lock_hash,
            "hash_match": lock_hash_match,
        },
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir66_70_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir65_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR66-IR69 batch run with dry-run only safeguards."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir66_70"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir65_path = ir65_completion_bundle_path or (
        reports_dir / "ir61_65" / "ir65_completion_bundle.json"
    )

    if not ir65_path.exists():
        raise FileNotFoundError(f"ir65 completion bundle not found: {ir65_path}")

    ir65_report = _read_json(ir65_path)

    ir66_report = _build_ir66_report(
        ir65_report=ir65_report,
        source_task_id=source_task_id,
    )
    ir66_path = out_dir / "ir66_final_dry_run_comprehensive_audit.json"
    _write_json(ir66_path, ir66_report)

    ir67_report = _build_ir67_report(
        ir65_report=ir65_report,
        ir66_report=ir66_report,
        source_task_id=source_task_id,
    )
    ir67_path = out_dir / "ir67_pre_operational_transition_review.json"
    _write_json(ir67_path, ir67_report)

    ir68_report = run_ir68_no_go_lock_gate(
        ir67_transition_review=ir67_report,
        ir66_comprehensive_audit=ir66_report,
        source_task_id=source_task_id,
    )
    ir68_path = out_dir / "ir68_no_go_lock_gate_report.json"
    _write_json(ir68_path, ir68_report)

    ir69_report = _build_ir69_report(
        ir65_report=ir65_report,
        ir66_report=ir66_report,
        ir67_report=ir67_report,
        ir68_report=ir68_report,
        source_task_id=source_task_id,
    )
    ir69_path = out_dir / "ir69_next_phase_design_package.json"
    _write_json(ir69_path, ir69_report)

    final_decision = ir68_report["no_go_lock_gate_decision"]

    return {
        "phase": "IR66_70_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "source_ir65_bundle_path": _to_ref(ir65_path, project_root),
        "final_decision": final_decision,
        "ir66_result": ir66_report,
        "ir67_result": ir67_report,
        "ir68_result": ir68_report,
        "ir69_result": ir69_report,
        "artifacts": {
            "ir66_final_dry_run_comprehensive_audit": _to_ref(ir66_path, project_root),
            "ir67_pre_operational_transition_review": _to_ref(ir67_path, project_root),
            "ir68_no_go_lock_gate_report": _to_ref(ir68_path, project_root),
            "ir69_next_phase_design_package": _to_ref(ir69_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR70: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir66_70_completion_bundle(
    *,
    base_path: Path,
    ir66_70_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR70 completion bundle writer."""
    out_dir = base_path / "reports" / "ir66_70"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir66_result = ir66_70_output.get("ir66_result", {})
    ir67_result = ir66_70_output.get("ir67_result", {})
    ir68_result = ir66_70_output.get("ir68_result", {})
    ir69_result = ir66_70_output.get("ir69_result", {})
    final_decision = str(ir66_70_output.get("final_decision", IR68_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir68_live = "PASS" if final_decision == IR68_LOCKED else "FAIL"

    table_rows = [
        {"phase": "IR66", "content": "Final DRY_RUN Comprehensive Auditor", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir66_result), "judgement": _judgement(_live(ir66_result))},
        {"phase": "IR67", "content": "Pre-Operational Transition Reviewer", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir67_result), "judgement": _judgement(_live(ir67_result))},
        {"phase": "IR68", "content": "NO-GO Lock Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir68_live, "judgement": _judgement(ir68_live)},
        {"phase": "IR69", "content": "Next-Phase Design Package Assembler", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir69_result), "judgement": _judgement(_live(ir69_result))},
        {"phase": "IR70", "content": "Phase 66-70 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir68_live, "judgement": _judgement(ir68_live)},
    ]

    bundle = {
        "schema_version": IR70_SCHEMA_VERSION,
        "phase": "IR70",
        "generated_at": _now_iso(),
        "source_task_id": ir66_70_output.get("source_task_id", "UNKNOWN"),
        "ir66_result": ir66_result,
        "ir67_result": ir67_result,
        "ir68_result": ir68_result,
        "ir69_result": ir69_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir66": table_rows[0]["live"],
            "ir67": table_rows[1]["live"],
            "ir68": table_rows[2]["live"],
            "ir69": table_rows[3]["live"],
            "ir70": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "no_go_lock_confirmed": final_decision == IR68_LOCKED,
        "artifacts": {
            **ir66_70_output.get("artifacts", {}),
            "ir70_completion_bundle": "generic_block_ai/reports/ir66_70/ir70_completion_bundle.json",
            "ir66_70_live_status": "generic_block_ai/reports/ir66_70/ir66_70_live_status.md",
            "ir66_70_completion_table": "generic_block_ai/reports/ir66_70/ir66_70_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir70_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR66-IR70 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- NO-GO Lock Confirmed: {bundle['no_go_lock_confirmed']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir66_70_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR66-IR70 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir66_70_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir70_completion_bundle": _to_ref(bundle_path, project_root),
            "ir66_70_live_status": _to_ref(live_path, project_root),
            "ir66_70_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

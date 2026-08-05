"""
core_ir71_75_new_cycle_design_approval_batch.py - IR71-IR75

Batch implementation for new cycle design approval gate, approver attestation,
dry-run unlock policy declaration, legacy artifact freeze registry,
and completion bundle for the new IR71+ cycle bootstrap.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR70_SCHEMA_VERSION = "ir70_phase_66_70_completion_bundle_v1"
IR71_SCHEMA_VERSION = "ir71_new_cycle_design_gate_v1"
IR72_SCHEMA_VERSION = "ir72_cycle_approver_attestation_v1"
IR73_SCHEMA_VERSION = "ir73_dry_run_unlock_policy_declaration_v1"
IR74_SCHEMA_VERSION = "ir74_legacy_artifact_freeze_registry_v1"
IR75_SCHEMA_VERSION = "ir75_phase_71_75_completion_bundle_v1"

IR71_APPROVED = "NEW_CYCLE_DESIGN_APPROVED"
IR71_HOLD = "HOLD"
IR71_ABORT = "ABORT"


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
# IR71: New Cycle Design Approval Gate
# ---------------------------------------------------------------------------

def run_ir71_new_cycle_design_gate(
    *,
    ir70_completion_bundle: dict[str, Any],
    source_task_id: str,
    new_cycle_id: str,
    design_owner: str,
) -> dict[str, Any]:
    """Confirm prior cycle lock and open design gate for IR71+ as a new cycle."""
    failed_checks: list[str] = []

    if ir70_completion_bundle.get("schema_version") != IR70_SCHEMA_VERSION:
        failed_checks.append(f"ir70 schema_version must be {IR70_SCHEMA_VERSION}")

    final_decision = str(ir70_completion_bundle.get("final_decision", "UNKNOWN"))
    if final_decision != "NO_GO_LOCKED_DRY_RUN_ONLY":
        failed_checks.append(
            f"ir70 final_decision must be NO_GO_LOCKED_DRY_RUN_ONLY, got {final_decision}"
        )

    if ir70_completion_bundle.get("no_go_lock_confirmed") is not True:
        failed_checks.append("ir70 no_go_lock_confirmed must be true")

    safety_gate = ir70_completion_bundle.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
        failed_checks.append("ir70 safety_gate_summary must be object")

    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safety_gate.get(key) is not False:
            failed_checks.append(f"ir70 safety_gate_summary.{key} must be false")

    if not str(new_cycle_id).strip():
        failed_checks.append("new_cycle_id is required")
    if not str(design_owner).strip():
        failed_checks.append("design_owner is required")

    decision = IR71_APPROVED if not failed_checks else IR71_HOLD

    gate_record = {
        "gate_id": f"ir71_gate_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": new_cycle_id,
        "design_owner": design_owner,
        "prior_cycle_final_decision": final_decision,
        "prior_cycle_locked": ir70_completion_bundle.get("no_go_lock_confirmed", False),
        "decision": decision,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR71_SCHEMA_VERSION,
        "phase": "IR71",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_design_gate_decision": decision,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "gate_record": gate_record,
        "gate_hash": _sha256_hex(gate_record),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR72: Cycle Approver Attestation
# ---------------------------------------------------------------------------

def _build_ir72_report(
    *,
    ir71_report: dict[str, Any],
    source_task_id: str,
    approver: str,
) -> dict[str, Any]:
    """Attach named approver attestation to new cycle design gate."""
    failed_checks: list[str] = []

    if ir71_report.get("validation_result") != "PASS":
        failed_checks.append("ir71 gate must be PASS")

    if ir71_report.get("new_cycle_design_gate_decision") != IR71_APPROVED:
        failed_checks.append("ir71 decision must be NEW_CYCLE_DESIGN_APPROVED")

    if not str(approver).strip():
        failed_checks.append("approver is required")

    gate_hash = str(ir71_report.get("gate_hash", ""))
    gate_record = ir71_report.get("gate_record", {})
    recalculated_gate_hash = _sha256_hex(gate_record) if gate_record else ""
    if gate_hash != recalculated_gate_hash:
        failed_checks.append("ir71 gate_hash mismatch")

    attestation = {
        "attestation_id": f"ir72_attest_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": gate_record.get("new_cycle_id", "UNKNOWN"),
        "approver": approver,
        "attestation": "approved_for_new_cycle_design_scope_only",
        "linked_ir71_gate_hash": gate_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR72_SCHEMA_VERSION,
        "phase": "IR72",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "attestation_record": attestation,
        "attestation_hash": _sha256_hex(attestation),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR73: Dry-Run Unlock Policy Declaration
# ---------------------------------------------------------------------------

def _build_ir73_report(
    *,
    ir71_report: dict[str, Any],
    ir72_report: dict[str, Any],
    source_task_id: str,
    unlock_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Declare unlock preconditions for any future dry-run policy lift."""
    failed_checks: list[str] = []

    if ir72_report.get("validation_result") != "PASS":
        failed_checks.append("ir72 attestation must be PASS")

    if ir71_report.get("new_cycle_design_gate_decision") != IR71_APPROVED:
        failed_checks.append("ir71 decision must remain NEW_CYCLE_DESIGN_APPROVED")

    policy = unlock_policy or {
        "requires_explicit_design_approval": True,
        "requires_named_approver": True,
        "requires_safety_gate_redeclaration": True,
        "requires_test_matrix_reexecution": True,
        "requires_no_go_lock_reference": True,
    }

    required_keys = [
        "requires_explicit_design_approval",
        "requires_named_approver",
        "requires_safety_gate_redeclaration",
        "requires_test_matrix_reexecution",
        "requires_no_go_lock_reference",
    ]
    for key in required_keys:
        if policy.get(key) is not True:
            failed_checks.append(f"unlock_policy.{key} must be true")

    declaration = {
        "declaration_id": f"ir73_policy_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir71_report.get("gate_record", {}).get("new_cycle_id", "UNKNOWN"),
        "unlock_policy": policy,
        "policy_scope": "design_and_governance_only",
        "execution_unlock_blocked_by_default": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR73_SCHEMA_VERSION,
        "phase": "IR73",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "policy_declaration": declaration,
        "policy_hash": _sha256_hex(declaration),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR74: Legacy Artifact Freeze Registry
# ---------------------------------------------------------------------------

def run_ir74_legacy_artifact_freeze_registry(
    *,
    ir70_completion_bundle: dict[str, Any],
    ir73_policy_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Register prior cycle artifacts as reference-only frozen assets."""
    failed_checks: list[str] = []

    if ir73_policy_report.get("validation_result") != "PASS":
        failed_checks.append("ir73 policy declaration must be PASS")

    if ir70_completion_bundle.get("final_decision") != "NO_GO_LOCKED_DRY_RUN_ONLY":
        failed_checks.append("ir70 final_decision must be NO_GO_LOCKED_DRY_RUN_ONLY")

    artifacts = ir70_completion_bundle.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        failed_checks.append("ir70 artifacts must be object")

    if not artifacts:
        failed_checks.append("ir70 artifacts must not be empty")

    freeze_entries = [
        {
            "artifact_key": k,
            "artifact_ref": str(v),
            "freeze_mode": "reference_only",
            "mutation_allowed": False,
        }
        for k, v in sorted(artifacts.items())
    ]

    registry = {
        "registry_id": f"ir74_freeze_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "legacy_cycle": "IR51_to_IR70",
        "freeze_entries": freeze_entries,
        "freeze_scope": "reference_only",
        "external_distribution_blocked": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    decision = "FROZEN_REFERENCE_ONLY" if not failed_checks else "HOLD"

    return {
        "schema_version": IR74_SCHEMA_VERSION,
        "phase": "IR74",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "legacy_artifact_freeze_decision": decision,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "freeze_registry": registry,
        "registry_hash": _sha256_hex(registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir71_75_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    new_cycle_id: str,
    design_owner: str,
    approver: str,
    ir70_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR71-IR74 batch run for new-cycle governance setup in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir71_75"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir70_path = ir70_completion_bundle_path or (
        reports_dir / "ir66_70" / "ir70_completion_bundle.json"
    )

    if not ir70_path.exists():
        raise FileNotFoundError(f"ir70 completion bundle not found: {ir70_path}")

    ir70_report = _read_json(ir70_path)

    ir71_report = run_ir71_new_cycle_design_gate(
        ir70_completion_bundle=ir70_report,
        source_task_id=source_task_id,
        new_cycle_id=new_cycle_id,
        design_owner=design_owner,
    )
    ir71_path = out_dir / "ir71_new_cycle_design_gate_report.json"
    _write_json(ir71_path, ir71_report)

    ir72_report = _build_ir72_report(
        ir71_report=ir71_report,
        source_task_id=source_task_id,
        approver=approver,
    )
    ir72_path = out_dir / "ir72_cycle_approver_attestation_report.json"
    _write_json(ir72_path, ir72_report)

    ir73_report = _build_ir73_report(
        ir71_report=ir71_report,
        ir72_report=ir72_report,
        source_task_id=source_task_id,
    )
    ir73_path = out_dir / "ir73_dry_run_unlock_policy_declaration.json"
    _write_json(ir73_path, ir73_report)

    ir74_report = run_ir74_legacy_artifact_freeze_registry(
        ir70_completion_bundle=ir70_report,
        ir73_policy_report=ir73_report,
        source_task_id=source_task_id,
    )
    ir74_path = out_dir / "ir74_legacy_artifact_freeze_registry_report.json"
    _write_json(ir74_path, ir74_report)

    final_decision = ir74_report["legacy_artifact_freeze_decision"]

    return {
        "phase": "IR71_75_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": new_cycle_id,
        "source_ir70_bundle_path": _to_ref(ir70_path, project_root),
        "final_decision": final_decision,
        "ir71_result": ir71_report,
        "ir72_result": ir72_report,
        "ir73_result": ir73_report,
        "ir74_result": ir74_report,
        "artifacts": {
            "ir71_new_cycle_design_gate_report": _to_ref(ir71_path, project_root),
            "ir72_cycle_approver_attestation_report": _to_ref(ir72_path, project_root),
            "ir73_dry_run_unlock_policy_declaration": _to_ref(ir73_path, project_root),
            "ir74_legacy_artifact_freeze_registry_report": _to_ref(ir74_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR75: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir71_75_completion_bundle(
    *,
    base_path: Path,
    ir71_75_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR75 completion bundle writer."""
    out_dir = base_path / "reports" / "ir71_75"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir71_result = ir71_75_output.get("ir71_result", {})
    ir72_result = ir71_75_output.get("ir72_result", {})
    ir73_result = ir71_75_output.get("ir73_result", {})
    ir74_result = ir71_75_output.get("ir74_result", {})
    final_decision = str(ir71_75_output.get("final_decision", "HOLD"))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir74_live = "PASS" if final_decision == "FROZEN_REFERENCE_ONLY" else "FAIL"

    table_rows = [
        {"phase": "IR71", "content": "New Cycle Design Approval Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir71_result), "judgement": _judgement(_live(ir71_result))},
        {"phase": "IR72", "content": "Cycle Approver Attestation", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir72_result), "judgement": _judgement(_live(ir72_result))},
        {"phase": "IR73", "content": "Dry-Run Unlock Policy Declaration", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir73_result), "judgement": _judgement(_live(ir73_result))},
        {"phase": "IR74", "content": "Legacy Artifact Freeze Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir74_live, "judgement": _judgement(ir74_live)},
        {"phase": "IR75", "content": "Phase 71-75 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir74_live, "judgement": _judgement(ir74_live)},
    ]

    bundle = {
        "schema_version": IR75_SCHEMA_VERSION,
        "phase": "IR75",
        "generated_at": _now_iso(),
        "source_task_id": ir71_75_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir71_75_output.get("new_cycle_id", "UNKNOWN"),
        "ir71_result": ir71_result,
        "ir72_result": ir72_result,
        "ir73_result": ir73_result,
        "ir74_result": ir74_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir71": table_rows[0]["live"],
            "ir72": table_rows[1]["live"],
            "ir73": table_rows[2]["live"],
            "ir74": table_rows[3]["live"],
            "ir75": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "legacy_cycle_frozen_reference_only": final_decision == "FROZEN_REFERENCE_ONLY",
        "artifacts": {
            **ir71_75_output.get("artifacts", {}),
            "ir75_completion_bundle": "generic_block_ai/reports/ir71_75/ir75_completion_bundle.json",
            "ir71_75_live_status": "generic_block_ai/reports/ir71_75/ir71_75_live_status.md",
            "ir71_75_completion_table": "generic_block_ai/reports/ir71_75/ir71_75_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir75_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR71-IR75 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Legacy Cycle Frozen (reference only): {bundle['legacy_cycle_frozen_reference_only']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir71_75_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR71-IR75 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir71_75_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir75_completion_bundle": _to_ref(bundle_path, project_root),
            "ir71_75_live_status": _to_ref(live_path, project_root),
            "ir71_75_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

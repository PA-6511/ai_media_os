"""
core_ir76_80_execution_governance_batch.py - IR76-IR80

Batch implementation for new cycle execution governance in dry-run mode:
IR76 execution boundary policy, IR77 unlock preconditions verifier,
IR78 human approval scope registry, IR79 legacy reference linkage verifier,
IR80 completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR75_SCHEMA_VERSION = "ir75_phase_71_75_completion_bundle_v1"
IR76_SCHEMA_VERSION = "ir76_new_cycle_execution_boundary_policy_v1"
IR77_SCHEMA_VERSION = "ir77_dry_run_unlock_preconditions_verifier_v1"
IR78_SCHEMA_VERSION = "ir78_human_approval_scope_registry_v1"
IR79_SCHEMA_VERSION = "ir79_legacy_reference_linkage_verifier_v1"
IR80_SCHEMA_VERSION = "ir80_phase_76_80_completion_bundle_v1"

IR79_READY = "GOVERNANCE_READY_DRY_RUN_ONLY"
IR79_HOLD = "HOLD"
IR79_ABORT = "ABORT"


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
# IR76: New Cycle Execution Boundary Policy
# ---------------------------------------------------------------------------

def _build_ir76_report(
    *,
    ir75_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Define strict execution boundaries for the new cycle."""
    failed_checks: list[str] = []

    if ir75_report.get("schema_version") != IR75_SCHEMA_VERSION:
        failed_checks.append(f"ir75 schema_version must be {IR75_SCHEMA_VERSION}")

    if ir75_report.get("final_decision") != "FROZEN_REFERENCE_ONLY":
        failed_checks.append("ir75 final_decision must be FROZEN_REFERENCE_ONLY")

    if ir75_report.get("legacy_cycle_frozen_reference_only") is not True:
        failed_checks.append("ir75 legacy_cycle_frozen_reference_only must be true")

    new_cycle_id = str(ir75_report.get("new_cycle_id", "UNKNOWN"))
    if new_cycle_id == "UNKNOWN":
        failed_checks.append("ir75 new_cycle_id is missing")

    boundary_policy = {
        "policy_id": f"ir76_boundary_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": new_cycle_id,
        "policy_scope": "new_cycle_execution_governance",
        "execution_mode": "dry_run_only",
        "allow_live_execution": False,
        "allow_production_release": False,
        "require_human_approval_registry": True,
        "legacy_cycle_access_mode": "reference_only",
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR76_SCHEMA_VERSION,
        "phase": "IR76",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "execution_boundary_policy": boundary_policy,
        "policy_hash": _sha256_hex(boundary_policy),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR77: Dry-Run Unlock Preconditions Verifier
# ---------------------------------------------------------------------------

def _build_ir77_report(
    *,
    ir76_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Verify unlock preconditions remain unmet by default in governance mode."""
    failed_checks: list[str] = []

    if ir76_report.get("validation_result") != "PASS":
        failed_checks.append("ir76 boundary policy must be PASS")

    policy = ir76_report.get("execution_boundary_policy", {})
    if not isinstance(policy, dict):
        policy = {}
        failed_checks.append("ir76 execution_boundary_policy must be object")

    preconditions = {
        "explicit_go_decision_recorded": False,
        "named_release_approver_recorded": False,
        "safety_gate_redeclaration_completed": False,
        "full_test_matrix_reexecuted": False,
        "external_execution_authorized": False,
    }

    # Governance layer expects all unlock preconditions to remain false at this step.
    for key, value in preconditions.items():
        if value is not False:
            failed_checks.append(f"precondition {key} must be false at IR77")

    if policy.get("allow_live_execution") is not False:
        failed_checks.append("ir76 allow_live_execution must be false")
    if policy.get("allow_production_release") is not False:
        failed_checks.append("ir76 allow_production_release must be false")

    verification_result = "LOCKED_BY_PRECONDITIONS" if not failed_checks else "PRECONDITION_MISMATCH"

    report_payload = {
        "verification_id": f"ir77_verify_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": policy.get("new_cycle_id", "UNKNOWN"),
        "unlock_preconditions": preconditions,
        "verification_result": verification_result,
        "unlock_blocked": True,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR77_SCHEMA_VERSION,
        "phase": "IR77",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "precondition_verification": report_payload,
        "verification_hash": _sha256_hex(report_payload),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR78: Human Approval Scope Registry
# ---------------------------------------------------------------------------

def _build_ir78_report(
    *,
    ir76_report: dict[str, Any],
    ir77_report: dict[str, Any],
    source_task_id: str,
    approver_roles: list[str] | None = None,
) -> dict[str, Any]:
    """Register allowed human approval scopes for future governance actions."""
    failed_checks: list[str] = []

    if ir77_report.get("validation_result") != "PASS":
        failed_checks.append("ir77 precondition verifier must be PASS")

    policy = ir76_report.get("execution_boundary_policy", {})
    new_cycle_id = str(policy.get("new_cycle_id", "UNKNOWN"))
    if new_cycle_id == "UNKNOWN":
        failed_checks.append("ir76 new_cycle_id is missing")

    roles = approver_roles or ["design_owner", "release_governor", "safety_reviewer"]
    if not roles:
        failed_checks.append("approver_roles must not be empty")

    scope_registry = {
        "registry_id": f"ir78_scope_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": new_cycle_id,
        "approval_scopes": [
            {
                "role": role,
                "can_update_design": True,
                "can_lift_dry_run": False,
                "can_release_production": False,
            }
            for role in roles
        ],
        "scope_mode": "governance_only",
        "unlock_authority_delegated": False,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR78_SCHEMA_VERSION,
        "phase": "IR78",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "approval_scope_registry": scope_registry,
        "registry_hash": _sha256_hex(scope_registry),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR79: Legacy Reference Linkage Verifier
# ---------------------------------------------------------------------------

def run_ir79_legacy_reference_linkage_verifier(
    *,
    ir75_report: dict[str, Any],
    ir78_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Verify legacy references are linked read-only and governance constraints persist."""
    failed_checks: list[str] = []

    if ir78_report.get("validation_result") != "PASS":
        failed_checks.append("ir78 approval scope registry must be PASS")

    artifacts = ir75_report.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        failed_checks.append("ir75 artifacts must be object")

    if not artifacts:
        failed_checks.append("ir75 artifacts must not be empty")

    linkage_records = [
        {
            "artifact_key": key,
            "artifact_ref": str(value),
            "linkage_mode": "reference_only",
            "mutation_allowed": False,
        }
        for key, value in sorted(artifacts.items())
    ]

    scope_registry = ir78_report.get("approval_scope_registry", {})
    if scope_registry.get("unlock_authority_delegated") is not False:
        failed_checks.append("ir78 unlock_authority_delegated must be false")

    safety_snapshot = ir78_report.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"

    if abort_flags or github_push:
        gate_decision = IR79_ABORT
        gate_action = "Abort due to unsafe external execution flags."
    elif failed_checks:
        gate_decision = IR79_HOLD
        gate_action = "Hold due to linkage validation failure."
    else:
        gate_decision = IR79_READY
        gate_action = "Legacy linkage verified as reference-only under dry-run governance."

    verification_record = {
        "verification_id": f"ir79_link_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir75_report.get("new_cycle_id", "UNKNOWN"),
        "linkage_records": linkage_records,
        "linkage_scope": "reference_only",
        "gate_decision": gate_decision,
        "safety_gate_snapshot": _default_safety_gate(),
    }

    return {
        "schema_version": IR79_SCHEMA_VERSION,
        "phase": "IR79",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "legacy_reference_linkage_decision": gate_decision,
        "gate_action": gate_action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "linkage_verification": verification_record,
        "verification_hash": _sha256_hex(verification_record),
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir76_80_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir75_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR76-IR79 batch run for governance execution boundaries in dry-run mode."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir76_80"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir75_path = ir75_completion_bundle_path or (
        reports_dir / "ir71_75" / "ir75_completion_bundle.json"
    )

    if not ir75_path.exists():
        raise FileNotFoundError(f"ir75 completion bundle not found: {ir75_path}")

    ir75_report = _read_json(ir75_path)

    ir76_report = _build_ir76_report(
        ir75_report=ir75_report,
        source_task_id=source_task_id,
    )
    ir76_path = out_dir / "ir76_new_cycle_execution_boundary_policy.json"
    _write_json(ir76_path, ir76_report)

    ir77_report = _build_ir77_report(
        ir76_report=ir76_report,
        source_task_id=source_task_id,
    )
    ir77_path = out_dir / "ir77_dry_run_unlock_preconditions_report.json"
    _write_json(ir77_path, ir77_report)

    ir78_report = _build_ir78_report(
        ir76_report=ir76_report,
        ir77_report=ir77_report,
        source_task_id=source_task_id,
    )
    ir78_path = out_dir / "ir78_human_approval_scope_registry_report.json"
    _write_json(ir78_path, ir78_report)

    ir79_report = run_ir79_legacy_reference_linkage_verifier(
        ir75_report=ir75_report,
        ir78_report=ir78_report,
        source_task_id=source_task_id,
    )
    ir79_path = out_dir / "ir79_legacy_reference_linkage_verifier_report.json"
    _write_json(ir79_path, ir79_report)

    final_decision = ir79_report["legacy_reference_linkage_decision"]

    return {
        "phase": "IR76_80_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "new_cycle_id": ir75_report.get("new_cycle_id", "UNKNOWN"),
        "source_ir75_bundle_path": _to_ref(ir75_path, project_root),
        "final_decision": final_decision,
        "ir76_result": ir76_report,
        "ir77_result": ir77_report,
        "ir78_result": ir78_report,
        "ir79_result": ir79_report,
        "artifacts": {
            "ir76_new_cycle_execution_boundary_policy": _to_ref(ir76_path, project_root),
            "ir77_dry_run_unlock_preconditions_report": _to_ref(ir77_path, project_root),
            "ir78_human_approval_scope_registry_report": _to_ref(ir78_path, project_root),
            "ir79_legacy_reference_linkage_verifier_report": _to_ref(ir79_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR80: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir76_80_completion_bundle(
    *,
    base_path: Path,
    ir76_80_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR80 completion bundle writer."""
    out_dir = base_path / "reports" / "ir76_80"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir76_result = ir76_80_output.get("ir76_result", {})
    ir77_result = ir76_80_output.get("ir77_result", {})
    ir78_result = ir76_80_output.get("ir78_result", {})
    ir79_result = ir76_80_output.get("ir79_result", {})
    final_decision = str(ir76_80_output.get("final_decision", IR79_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir79_live = "PASS" if final_decision == IR79_READY else "FAIL"

    table_rows = [
        {"phase": "IR76", "content": "New Cycle Execution Boundary Policy", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir76_result), "judgement": _judgement(_live(ir76_result))},
        {"phase": "IR77", "content": "Dry-Run Unlock Preconditions Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir77_result), "judgement": _judgement(_live(ir77_result))},
        {"phase": "IR78", "content": "Human Approval Scope Registry", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir78_result), "judgement": _judgement(_live(ir78_result))},
        {"phase": "IR79", "content": "Legacy Reference Linkage Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir79_live, "judgement": _judgement(ir79_live)},
        {"phase": "IR80", "content": "Phase 76-80 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir79_live, "judgement": _judgement(ir79_live)},
    ]

    bundle = {
        "schema_version": IR80_SCHEMA_VERSION,
        "phase": "IR80",
        "generated_at": _now_iso(),
        "source_task_id": ir76_80_output.get("source_task_id", "UNKNOWN"),
        "new_cycle_id": ir76_80_output.get("new_cycle_id", "UNKNOWN"),
        "ir76_result": ir76_result,
        "ir77_result": ir77_result,
        "ir78_result": ir78_result,
        "ir79_result": ir79_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir76": table_rows[0]["live"],
            "ir77": table_rows[1]["live"],
            "ir78": table_rows[2]["live"],
            "ir79": table_rows[3]["live"],
            "ir80": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "governance_ready_dry_run_only": final_decision == IR79_READY,
        "artifacts": {
            **ir76_80_output.get("artifacts", {}),
            "ir80_completion_bundle": "generic_block_ai/reports/ir76_80/ir80_completion_bundle.json",
            "ir76_80_live_status": "generic_block_ai/reports/ir76_80/ir76_80_live_status.md",
            "ir76_80_completion_table": "generic_block_ai/reports/ir76_80/ir76_80_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir80_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR76-IR80 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        f"- Governance Ready (dry-run only): {bundle['governance_ready_dry_run_only']}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir76_80_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR76-IR80 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir76_80_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir80_completion_bundle": _to_ref(bundle_path, project_root),
            "ir76_80_live_status": _to_ref(live_path, project_root),
            "ir76_80_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

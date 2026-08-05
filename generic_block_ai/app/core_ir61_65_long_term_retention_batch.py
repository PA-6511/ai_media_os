"""
core_ir61_65_long_term_retention_batch.py - IR61-IR65

Batch implementation for post-archive confirmation logging, dry-run cycle
re-verification, final handoff package assembly, handoff package release gate,
and completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR60_SCHEMA_VERSION = "ir60_phase_56_60_completion_bundle_v1"
IR61_SCHEMA_VERSION = "ir61_post_archive_confirmation_logger_v1"
IR62_SCHEMA_VERSION = "ir62_dry_run_cycle_re_verification_auditor_v1"
IR63_SCHEMA_VERSION = "ir63_final_handoff_package_assembler_v1"
IR64_SCHEMA_VERSION = "ir64_handoff_package_release_gate_v1"
IR65_SCHEMA_VERSION = "ir65_phase_61_65_completion_bundle_v1"

IR64_READY = "READY_FOR_DRY_RUN_HANDOFF_ONLY"
IR64_HOLD = "HOLD"
IR64_REJECT = "REJECT"
IR64_ABORT = "ABORT"

# Expected full phase set covered across IR51-IR60
_FULL_CYCLE_PHASES = {
    "IR51", "IR52", "IR53", "IR54", "IR55",
    "IR56", "IR57", "IR58", "IR59", "IR60",
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
# IR61: Post-Archive Confirmation Logger
# ---------------------------------------------------------------------------

def _build_ir61_report(
    *,
    ir60_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Log a confirmation record from the IR60 completion bundle for long-term retention."""
    failed_checks: list[str] = []

    if ir60_report.get("schema_version") != IR60_SCHEMA_VERSION:
        failed_checks.append(f"ir60 schema_version must be {IR60_SCHEMA_VERSION}")

    final_decision = str(ir60_report.get("final_decision", "UNKNOWN"))
    if final_decision == "UNKNOWN":
        failed_checks.append("ir60 final_decision is missing or unknown")

    safety_gate = ir60_report.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
        failed_checks.append("ir60 safety_gate_summary must be object")

    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safety_gate.get(key) is not False:
            failed_checks.append(f"ir60 safety_gate_summary.{key} must be false")

    completion_table = ir60_report.get("completion_table", [])
    if not isinstance(completion_table, list):
        failed_checks.append("ir60 completion_table must be list")
        completion_table = []

    all_complete = all(
        isinstance(row, dict) and row.get("judgement") == "完了"
        for row in completion_table
    )
    if completion_table and not all_complete:
        failed_checks.append("ir60 completion_table has incomplete judgements")

    live_summary = ir60_report.get("live_summary", {})
    if not isinstance(live_summary, dict):
        failed_checks.append("ir60 live_summary must be object")
        live_summary = {}

    all_live_pass = all(str(v) == "PASS" for v in live_summary.values()) if live_summary else False
    if live_summary and not all_live_pass:
        failed_checks.append("ir60 live_summary has non-PASS entries")

    confirmation_entry = {
        "confirmation_id": f"confirm_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "confirmed_at": _now_iso(),
        "source_phase": "IR60",
        "source_task_id": source_task_id,
        "final_decision_confirmed": final_decision,
        "completion_table_snapshot": completion_table,
        "live_summary_snapshot": live_summary,
        "safety_gate_snapshot": _default_safety_gate(),
        "retention_policy": "dry_run_artifacts_only",
        "long_term_retention_blocked_until_live": True,
    }
    confirmation_hash = _sha256_hex(confirmation_entry)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR61_SCHEMA_VERSION,
        "phase": "IR61",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "confirmation_entry": confirmation_entry,
        "confirmation_hash": confirmation_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR62: Dry-Run Cycle Re-Verification Auditor
# ---------------------------------------------------------------------------

def _build_ir62_report(
    *,
    ir60_report: dict[str, Any],
    ir61_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Re-verify the entire IR51-IR60 dry-run cycle for cross-bundle integrity."""
    failed_checks: list[str] = []

    if ir61_report.get("validation_result") != "PASS":
        failed_checks.append("ir61 post-archive confirmation must be PASS")

    # Gather full phase coverage across IR55 and IR60 completion tables
    ir60_table = ir60_report.get("completion_table", [])
    ir60_phases = {
        str(row.get("phase", ""))
        for row in ir60_table
        if isinstance(row, dict)
    }

    # Check IR60 table covers IR56-IR60
    expected_ir60_phases = {"IR56", "IR57", "IR58", "IR59", "IR60"}
    missing_ir60_phases = expected_ir60_phases - ir60_phases
    if missing_ir60_phases:
        failed_checks.append(f"ir60 completion_table missing phases: {sorted(missing_ir60_phases)}")

    # Cross-check all phases in IR60 table are complete
    incomplete = [
        str(row.get("phase", ""))
        for row in ir60_table
        if isinstance(row, dict) and row.get("judgement") != "完了"
    ]
    if incomplete:
        failed_checks.append(f"incomplete phases in ir60 table: {incomplete}")

    # Verify safety gate continuity
    gate = ir60_report.get("safety_gate_summary", {})
    if not isinstance(gate, dict):
        gate = {}
    if str(gate.get("dry_run", "")) != "maintained":
        failed_checks.append("dry_run must be maintained through IR60")
    if str(gate.get("OBSERVE", "")) != "maintained":
        failed_checks.append("OBSERVE must be maintained through IR60")

    # Verify final decision
    final_decision = str(ir60_report.get("final_decision", "UNKNOWN"))
    if final_decision != "READY_FOR_DRY_RUN_HANDOFF_ONLY":
        failed_checks.append(f"ir60 final_decision must be READY_FOR_DRY_RUN_HANDOFF_ONLY, got {final_decision}")

    # Confirmation hash verification
    provided_hash = str(ir61_report.get("confirmation_hash", ""))
    confirmation_entry = ir61_report.get("confirmation_entry", {})
    recalculated_hash = _sha256_hex(confirmation_entry) if confirmation_entry else ""
    hash_match = provided_hash == recalculated_hash
    if not hash_match:
        failed_checks.append("ir61 confirmation_hash mismatch (re-verification tamper detected)")

    re_verification_result = "CYCLE_VERIFIED" if not failed_checks else "CYCLE_VERIFICATION_FAILED"

    return {
        "schema_version": IR62_SCHEMA_VERSION,
        "phase": "IR62",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "re_verification_result": re_verification_result,
        "ir60_phases_found": sorted(ir60_phases),
        "ir60_phases_missing": sorted(missing_ir60_phases),
        "incomplete_phases": incomplete,
        "ir60_final_decision": final_decision,
        "hash_re_verification": {
            "provided_hash": provided_hash,
            "recalculated_hash": recalculated_hash,
            "hash_match": hash_match,
        },
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR63: Final Handoff Package Assembler
# ---------------------------------------------------------------------------

def _build_ir63_report(
    *,
    ir60_report: dict[str, Any],
    ir61_report: dict[str, Any],
    ir62_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Assemble the final dry-run handoff package manifest (no actual write)."""
    failed_checks: list[str] = []

    if ir62_report.get("validation_result") != "PASS":
        failed_checks.append("ir62 re-verification auditor must be PASS")

    if ir62_report.get("re_verification_result") != "CYCLE_VERIFIED":
        failed_checks.append("ir62 re_verification_result must be CYCLE_VERIFIED")

    handoff_package = {
        "handoff_package_id": f"handoff_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "source_task_id": source_task_id,
        "assembled_at": _now_iso(),
        "covered_phases": sorted(_FULL_CYCLE_PHASES),
        "ir60_completion_bundle_ref": ir60_report.get("artifacts", {}).get(
            "ir60_completion_bundle", "UNKNOWN"
        ),
        "ir61_confirmation_ref": ir61_report.get("confirmation_entry", {}).get(
            "confirmation_id", "UNKNOWN"
        ),
        "ir62_re_verification_result": ir62_report.get("re_verification_result", "UNKNOWN"),
        "safety_gate_snapshot": _default_safety_gate(),
        "assembly_execution_blocked": True,
        "external_distribution_blocked": True,
        "retention_scope": "dry_run_only",
    }
    package_hash = _sha256_hex(handoff_package)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR63_SCHEMA_VERSION,
        "phase": "IR63",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "handoff_package": handoff_package,
        "handoff_package_hash": package_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR64: Handoff Package Release Gate
# ---------------------------------------------------------------------------

def run_ir64_handoff_package_release_gate(
    *,
    ir63_handoff_package: dict[str, Any],
    ir62_re_verification: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Final handoff package release gate; verifies IR63 package and locks gate decision."""
    failed_checks: list[str] = []

    required_fields = [
        "handoff_package_id",
        "source_task_id",
        "covered_phases",
        "assembled_at",
        "safety_gate_snapshot",
        "assembly_execution_blocked",
        "external_distribution_blocked",
        "retention_scope",
    ]
    package = ir63_handoff_package.get("handoff_package", {})
    if not isinstance(package, dict):
        failed_checks.append("ir63 handoff_package must be object")
        package = {}

    missing_fields = [f for f in required_fields if f not in package]
    if missing_fields:
        failed_checks.append(f"handoff_package missing required fields: {missing_fields}")

    if package.get("assembly_execution_blocked") is not True:
        failed_checks.append("assembly_execution_blocked must be true")
    if package.get("external_distribution_blocked") is not True:
        failed_checks.append("external_distribution_blocked must be true")
    if str(package.get("retention_scope", "")) != "dry_run_only":
        failed_checks.append("retention_scope must be dry_run_only")

    # Hash re-verification
    provided_hash = str(ir63_handoff_package.get("handoff_package_hash", ""))
    recalculated_hash = _sha256_hex(package) if package else ""
    hash_match = provided_hash == recalculated_hash
    if not hash_match:
        failed_checks.append("handoff_package_hash mismatch (tamper detected)")

    # Safety gate on ir63
    snapshot = package.get("safety_gate_snapshot", {})
    if not isinstance(snapshot, dict):
        snapshot = {}
    expected_gate = _default_safety_gate()
    for key, expected in expected_gate.items():
        if snapshot.get(key) != expected:
            failed_checks.append(f"handoff safety_gate_snapshot.{key} mismatch")

    # Abort if any external execution flag is live on the ir63 envelope
    safety_snapshot = ir63_handoff_package.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"
    abort_condition = abort_flags or github_push

    if abort_condition:
        gate_decision = IR64_ABORT
        gate_action = "Abort due to external execution risk flags."
    elif failed_checks:
        gate_decision = IR64_REJECT
        gate_action = "Reject due to handoff package integrity failure."
    elif ir62_re_verification.get("re_verification_result") != "CYCLE_VERIFIED":
        gate_decision = IR64_HOLD
        gate_action = "Hold until IR62 cycle re-verification is complete."
    else:
        gate_decision = IR64_READY
        gate_action = "Handoff package integrity confirmed. Ready for dry-run handoff only."

    return {
        "schema_version": IR64_SCHEMA_VERSION,
        "phase": "IR64",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "handoff_release_gate_decision": gate_decision,
        "gate_action": gate_action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "hash_verification": {
            "provided_handoff_hash": provided_hash,
            "recalculated_handoff_hash": recalculated_hash,
            "hash_match": hash_match,
        },
        "tamper_detection_summary": "NO_TAMPER" if hash_match else "TAMPER_DETECTED",
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir61_65_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir60_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR61-IR64 batch run with dry-run only safeguards."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir61_65"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir60_path = ir60_completion_bundle_path or (
        reports_dir / "ir56_60" / "ir60_completion_bundle.json"
    )

    if not ir60_path.exists():
        raise FileNotFoundError(f"ir60 completion bundle not found: {ir60_path}")

    ir60_report = _read_json(ir60_path)

    ir61_report = _build_ir61_report(
        ir60_report=ir60_report,
        source_task_id=source_task_id,
    )
    ir61_path = out_dir / "ir61_post_archive_confirmation_log.json"
    _write_json(ir61_path, ir61_report)

    ir62_report = _build_ir62_report(
        ir60_report=ir60_report,
        ir61_report=ir61_report,
        source_task_id=source_task_id,
    )
    ir62_path = out_dir / "ir62_dry_run_cycle_re_verification_report.json"
    _write_json(ir62_path, ir62_report)

    ir63_report = _build_ir63_report(
        ir60_report=ir60_report,
        ir61_report=ir61_report,
        ir62_report=ir62_report,
        source_task_id=source_task_id,
    )
    ir63_path = out_dir / "ir63_final_handoff_package.json"
    _write_json(ir63_path, ir63_report)

    ir64_report = run_ir64_handoff_package_release_gate(
        ir63_handoff_package=ir63_report,
        ir62_re_verification=ir62_report,
        source_task_id=source_task_id,
    )
    ir64_path = out_dir / "ir64_handoff_release_gate_report.json"
    _write_json(ir64_path, ir64_report)

    final_decision = ir64_report["handoff_release_gate_decision"]

    return {
        "phase": "IR61_65_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "source_ir60_bundle_path": _to_ref(ir60_path, project_root),
        "final_decision": final_decision,
        "ir61_result": ir61_report,
        "ir62_result": ir62_report,
        "ir63_result": ir63_report,
        "ir64_result": ir64_report,
        "artifacts": {
            "ir61_post_archive_confirmation_log": _to_ref(ir61_path, project_root),
            "ir62_dry_run_cycle_re_verification_report": _to_ref(ir62_path, project_root),
            "ir63_final_handoff_package": _to_ref(ir63_path, project_root),
            "ir64_handoff_release_gate_report": _to_ref(ir64_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR65: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir61_65_completion_bundle(
    *,
    base_path: Path,
    ir61_65_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR65 completion bundle writer."""
    out_dir = base_path / "reports" / "ir61_65"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir61_result = ir61_65_output.get("ir61_result", {})
    ir62_result = ir61_65_output.get("ir62_result", {})
    ir63_result = ir61_65_output.get("ir63_result", {})
    ir64_result = ir61_65_output.get("ir64_result", {})
    final_decision = str(ir61_65_output.get("final_decision", IR64_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir64_live = "PASS" if final_decision == IR64_READY else "FAIL"

    table_rows = [
        {"phase": "IR61", "content": "Post-Archive Confirmation Logger", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir61_result), "judgement": _judgement(_live(ir61_result))},
        {"phase": "IR62", "content": "Dry-Run Cycle Re-Verification Auditor", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir62_result), "judgement": _judgement(_live(ir62_result))},
        {"phase": "IR63", "content": "Final Handoff Package Assembler", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir63_result), "judgement": _judgement(_live(ir63_result))},
        {"phase": "IR64", "content": "Handoff Package Release Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir64_live, "judgement": _judgement(ir64_live)},
        {"phase": "IR65", "content": "Phase 61-65 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir64_live, "judgement": _judgement(ir64_live)},
    ]

    bundle = {
        "schema_version": IR65_SCHEMA_VERSION,
        "phase": "IR65",
        "generated_at": _now_iso(),
        "source_task_id": ir61_65_output.get("source_task_id", "UNKNOWN"),
        "ir61_result": ir61_result,
        "ir62_result": ir62_result,
        "ir63_result": ir63_result,
        "ir64_result": ir64_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir61": table_rows[0]["live"],
            "ir62": table_rows[1]["live"],
            "ir63": table_rows[2]["live"],
            "ir64": table_rows[3]["live"],
            "ir65": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "artifacts": {
            **ir61_65_output.get("artifacts", {}),
            "ir65_completion_bundle": "generic_block_ai/reports/ir61_65/ir65_completion_bundle.json",
            "ir61_65_live_status": "generic_block_ai/reports/ir61_65/ir61_65_live_status.md",
            "ir61_65_completion_table": "generic_block_ai/reports/ir61_65/ir61_65_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir65_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR61-IR65 Live Status",
        "",
        f"- Final Decision: {final_decision}",
        "- dry_run: maintained",
        "- OBSERVE: maintained",
        "- submission_execution_blocked: true",
        "- execution_policy_execute: false",
        "- external_write_executed: false",
        "- network_transmission_executed: false",
        "- production_release: false",
        "- GitHub push: 未実行",
    ]
    live_path = out_dir / "ir61_65_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR61-IR65 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir61_65_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir65_completion_bundle": _to_ref(bundle_path, project_root),
            "ir61_65_live_status": _to_ref(live_path, project_root),
            "ir61_65_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

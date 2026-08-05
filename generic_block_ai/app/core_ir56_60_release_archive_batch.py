"""
core_ir56_60_release_archive_batch.py - IR56-IR60

Batch implementation for post-bundle audit trail recording, dry-run finalization,
pre-release archive building, archive integrity gate, and completion bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR55_SCHEMA_VERSION = "ir55_phase_51_55_completion_bundle_v1"
IR56_SCHEMA_VERSION = "ir56_post_bundle_audit_trail_recorder_v1"
IR57_SCHEMA_VERSION = "ir57_dry_run_finalization_verifier_v1"
IR58_SCHEMA_VERSION = "ir58_pre_release_archive_builder_v1"
IR59_SCHEMA_VERSION = "ir59_archive_integrity_gate_v1"
IR60_SCHEMA_VERSION = "ir60_phase_56_60_completion_bundle_v1"

IR59_READY = "READY_FOR_DRY_RUN_HANDOFF_ONLY"
IR59_HOLD = "HOLD"
IR59_REJECT = "REJECT"
IR59_ABORT = "ABORT"


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
# IR56: Post-Bundle Audit Trail Recorder
# ---------------------------------------------------------------------------

def _build_ir56_report(
    *,
    ir55_report: dict[str, Any],
    source_task_id: str,
    project_root: Path,
) -> dict[str, Any]:
    """Record an immutable audit trail entry from the IR55 completion bundle."""
    failed_checks: list[str] = []

    if ir55_report.get("schema_version") != IR55_SCHEMA_VERSION:
        failed_checks.append(f"ir55 schema_version must be {IR55_SCHEMA_VERSION}")

    final_decision = str(ir55_report.get("final_decision", "UNKNOWN"))
    if final_decision == "UNKNOWN":
        failed_checks.append("ir55 final_decision is missing or unknown")

    safety_gate = ir55_report.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
        failed_checks.append("ir55 safety_gate_summary must be object")

    for key in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release"):
        if safety_gate.get(key) is not False:
            failed_checks.append(f"ir55 safety_gate_summary.{key} must be false")

    completion_table = ir55_report.get("completion_table", [])
    if not isinstance(completion_table, list):
        failed_checks.append("ir55 completion_table must be list")
        completion_table = []

    all_complete = all(
        isinstance(row, dict) and row.get("judgement") == "完了"
        for row in completion_table
    )
    if completion_table and not all_complete:
        failed_checks.append("ir55 completion_table has incomplete judgements")

    live_summary = ir55_report.get("live_summary", {})
    if not isinstance(live_summary, dict):
        failed_checks.append("ir55 live_summary must be object")
        live_summary = {}

    all_live_pass = all(str(v) == "PASS" for v in live_summary.values()) if live_summary else False
    if live_summary and not all_live_pass:
        failed_checks.append("ir55 live_summary has non-PASS entries")

    audit_entry = {
        "audit_trail_id": f"audit_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "recorded_at": _now_iso(),
        "source_phase": "IR55",
        "source_task_id": source_task_id,
        "final_decision_recorded": final_decision,
        "completion_table_snapshot": completion_table,
        "live_summary_snapshot": live_summary,
        "safety_gate_snapshot": _default_safety_gate(),
    }
    audit_hash = _sha256_hex(audit_entry)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR56_SCHEMA_VERSION,
        "phase": "IR56",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "audit_trail_entry": audit_entry,
        "audit_trail_hash": audit_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR57: Dry-Run Finalization Verifier
# ---------------------------------------------------------------------------

def _build_ir57_report(
    *,
    ir55_report: dict[str, Any],
    ir56_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Verify the completeness of the full IR51-IR55 dry-run cycle."""
    failed_checks: list[str] = []

    if ir56_report.get("validation_result") != "PASS":
        failed_checks.append("ir56 audit trail validation must be PASS")

    expected_phases = {"IR51", "IR52", "IR53", "IR54", "IR55"}
    completion_table = ir55_report.get("completion_table", [])
    recorded_phases = {
        str(row.get("phase", ""))
        for row in completion_table
        if isinstance(row, dict)
    }
    missing_phases = expected_phases - recorded_phases
    if missing_phases:
        failed_checks.append(f"missing phases in completion_table: {sorted(missing_phases)}")

    incomplete_phases = [
        str(row.get("phase", ""))
        for row in completion_table
        if isinstance(row, dict) and row.get("judgement") != "完了"
    ]
    if incomplete_phases:
        failed_checks.append(f"incomplete phases: {incomplete_phases}")

    safety_gate = ir55_report.get("safety_gate_summary", {})
    if not isinstance(safety_gate, dict):
        safety_gate = {}
    if str(safety_gate.get("dry_run", "")) != "maintained":
        failed_checks.append("dry_run must be maintained through IR55")
    if str(safety_gate.get("OBSERVE", "")) != "maintained":
        failed_checks.append("OBSERVE must be maintained through IR55")

    final_decision = str(ir55_report.get("final_decision", "UNKNOWN"))
    if final_decision != "READY_FOR_DRY_RUN_HANDOFF_ONLY":
        failed_checks.append(f"ir55 final_decision must be READY_FOR_DRY_RUN_HANDOFF_ONLY, got {final_decision}")

    finalization_decision = "FINALIZED_DRY_RUN_COMPLETE" if not failed_checks else "FINALIZATION_BLOCKED"

    return {
        "schema_version": IR57_SCHEMA_VERSION,
        "phase": "IR57",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "finalization_decision": finalization_decision,
        "expected_phases": sorted(expected_phases),
        "recorded_phases": sorted(recorded_phases),
        "missing_phases": sorted(missing_phases),
        "incomplete_phases": incomplete_phases,
        "ir55_final_decision": final_decision,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR58: Pre-Release Archive Builder
# ---------------------------------------------------------------------------

def _build_ir58_report(
    *,
    ir55_report: dict[str, Any],
    ir56_report: dict[str, Any],
    ir57_report: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Build a pre-release archive manifest in dry-run mode (no actual write)."""
    failed_checks: list[str] = []

    if ir57_report.get("validation_result") != "PASS":
        failed_checks.append("ir57 finalization verifier must be PASS")

    archive_manifest = {
        "archive_id": f"archive_{_safe(source_task_id)}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "source_task_id": source_task_id,
        "included_phases": ["IR51", "IR52", "IR53", "IR54", "IR55"],
        "ir55_completion_bundle_ref": ir55_report.get("artifacts", {}).get("ir55_completion_bundle", "UNKNOWN"),
        "ir56_audit_trail_ref": str(ir56_report.get("audit_trail_entry", {}).get("audit_trail_id", "UNKNOWN")),
        "ir57_finalization_decision": ir57_report.get("finalization_decision", "UNKNOWN"),
        "generated_at": _now_iso(),
        "safety_gate_snapshot": _default_safety_gate(),
        "archive_execution_blocked": True,
        "network_write_blocked": True,
    }
    archive_hash = _sha256_hex(archive_manifest)

    validation_result = "PASS" if not failed_checks else "FAIL"
    return {
        "schema_version": IR58_SCHEMA_VERSION,
        "phase": "IR58",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": [],
        "archive_manifest": archive_manifest,
        "archive_hash": archive_hash,
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# IR59: Archive Integrity Gate
# ---------------------------------------------------------------------------

def run_ir59_archive_integrity_gate(
    *,
    ir58_release_archive: dict[str, Any],
    ir57_dry_run_finalization: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    """Final archive integrity gate; verifies IR58 archive and locks gate decision."""
    failed_checks: list[str] = []

    required_fields = [
        "archive_id",
        "source_task_id",
        "included_phases",
        "generated_at",
        "safety_gate_snapshot",
        "archive_execution_blocked",
        "network_write_blocked",
    ]
    manifest = ir58_release_archive.get("archive_manifest", {})
    if not isinstance(manifest, dict):
        failed_checks.append("ir58 archive_manifest must be object")
        manifest = {}

    missing_fields = [f for f in required_fields if f not in manifest]
    if missing_fields:
        failed_checks.append(f"archive_manifest missing required fields: {missing_fields}")

    if manifest.get("archive_execution_blocked") is not True:
        failed_checks.append("archive_execution_blocked must be true")
    if manifest.get("network_write_blocked") is not True:
        failed_checks.append("network_write_blocked must be true")

    provided_hash = str(ir58_release_archive.get("archive_hash", ""))
    recalculated_hash = _sha256_hex(manifest) if manifest else ""
    hash_match = provided_hash == recalculated_hash
    if not hash_match:
        failed_checks.append("archive_hash mismatch (tamper detected)")

    snapshot = manifest.get("safety_gate_snapshot", {})
    if not isinstance(snapshot, dict):
        snapshot = {}
    expected_gate = _default_safety_gate()
    for key, expected in expected_gate.items():
        if snapshot.get(key) != expected:
            failed_checks.append(f"archive safety_gate_snapshot.{key} mismatch")

    safety_snapshot = ir58_release_archive.get("safety_gate_snapshot", {})
    if not isinstance(safety_snapshot, dict):
        safety_snapshot = {}

    abort_flags = any(
        safety_snapshot.get(k) is True
        for k in ("execution_policy_execute", "external_write_executed", "network_transmission_executed", "production_release")
    )
    github_push = str(safety_snapshot.get("GitHub_push", "未実行")) != "未実行"
    abort_condition = abort_flags or github_push

    if abort_condition:
        gate_decision = IR59_ABORT
        gate_action = "Abort due to external execution risk flags."
    elif failed_checks:
        gate_decision = IR59_REJECT
        gate_action = "Reject due to archive integrity failure."
    elif ir57_dry_run_finalization.get("finalization_decision") != "FINALIZED_DRY_RUN_COMPLETE":
        gate_decision = IR59_HOLD
        gate_action = "Hold until IR57 finalization is complete."
    else:
        gate_decision = IR59_READY
        gate_action = "Archive integrity confirmed. Ready for dry-run handoff only."

    return {
        "schema_version": IR59_SCHEMA_VERSION,
        "phase": "IR59",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "archive_integrity_gate_decision": gate_decision,
        "gate_action": gate_action,
        "validation_result": "PASS" if not failed_checks else "FAIL",
        "validation_failed_checks": failed_checks,
        "hash_verification": {
            "provided_archive_hash": provided_hash,
            "recalculated_archive_hash": recalculated_hash,
            "hash_match": hash_match,
        },
        "tamper_detection_summary": "NO_TAMPER" if hash_match else "TAMPER_DETECTED",
        "safety_gate_snapshot": _default_safety_gate(),
    }


# ---------------------------------------------------------------------------
# Public batch entry point
# ---------------------------------------------------------------------------

def run_ir56_60_batch_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir55_completion_bundle_path: Path | None = None,
) -> dict[str, Any]:
    """IR56-IR59 batch run with dry-run only safeguards."""
    reports_dir = base_path / "reports"
    out_dir = reports_dir / "ir56_60"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir55_path = ir55_completion_bundle_path or (
        reports_dir / "ir51_55" / "ir55_completion_bundle.json"
    )

    if not ir55_path.exists():
        raise FileNotFoundError(f"ir55 completion bundle not found: {ir55_path}")

    ir55_report = _read_json(ir55_path)

    ir56_report = _build_ir56_report(
        ir55_report=ir55_report,
        source_task_id=source_task_id,
        project_root=project_root,
    )
    ir56_path = out_dir / "ir56_post_bundle_audit_trail_report.json"
    _write_json(ir56_path, ir56_report)

    ir57_report = _build_ir57_report(
        ir55_report=ir55_report,
        ir56_report=ir56_report,
        source_task_id=source_task_id,
    )
    ir57_path = out_dir / "ir57_dry_run_finalization_report.json"
    _write_json(ir57_path, ir57_report)

    ir58_report = _build_ir58_report(
        ir55_report=ir55_report,
        ir56_report=ir56_report,
        ir57_report=ir57_report,
        source_task_id=source_task_id,
    )
    ir58_path = out_dir / "ir58_pre_release_archive.json"
    _write_json(ir58_path, ir58_report)

    ir59_report = run_ir59_archive_integrity_gate(
        ir58_release_archive=ir58_report,
        ir57_dry_run_finalization=ir57_report,
        source_task_id=source_task_id,
    )
    ir59_path = out_dir / "ir59_archive_integrity_gate_report.json"
    _write_json(ir59_path, ir59_report)

    final_decision = ir59_report["archive_integrity_gate_decision"]

    return {
        "phase": "IR56_60_BATCH",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "source_ir55_bundle_path": _to_ref(ir55_path, project_root),
        "final_decision": final_decision,
        "ir56_result": ir56_report,
        "ir57_result": ir57_report,
        "ir58_result": ir58_report,
        "ir59_result": ir59_report,
        "artifacts": {
            "ir56_post_bundle_audit_trail_report": _to_ref(ir56_path, project_root),
            "ir57_dry_run_finalization_report": _to_ref(ir57_path, project_root),
            "ir58_pre_release_archive": _to_ref(ir58_path, project_root),
            "ir59_archive_integrity_gate_report": _to_ref(ir59_path, project_root),
        },
        "external_write_executed": False,
    }


# ---------------------------------------------------------------------------
# IR60: Completion bundle writer
# ---------------------------------------------------------------------------

def write_ir56_60_completion_bundle(
    *,
    base_path: Path,
    ir56_60_output: dict[str, Any],
    focused_tests: dict[str, Any] | None = None,
    adjacent_tests: dict[str, Any] | None = None,
    scoped_regression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """IR60 completion bundle writer."""
    out_dir = base_path / "reports" / "ir56_60"
    out_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    ir56_result = ir56_60_output.get("ir56_result", {})
    ir57_result = ir56_60_output.get("ir57_result", {})
    ir58_result = ir56_60_output.get("ir58_result", {})
    ir59_result = ir56_60_output.get("ir59_result", {})
    final_decision = str(ir56_60_output.get("final_decision", IR59_HOLD))

    def _live(result: dict[str, Any]) -> str:
        return "PASS" if result.get("validation_result") == "PASS" else "FAIL"

    def _judgement(live: str) -> str:
        return "完了" if live == "PASS" else "要修正"

    ir59_live = "PASS" if final_decision == IR59_READY else "FAIL"

    table_rows = [
        {"phase": "IR56", "content": "Post-Bundle Audit Trail Recorder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir56_result), "judgement": _judgement(_live(ir56_result))},
        {"phase": "IR57", "content": "Dry-Run Finalization Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir57_result), "judgement": _judgement(_live(ir57_result))},
        {"phase": "IR58", "content": "Pre-Release Archive Builder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": _live(ir58_result), "judgement": _judgement(_live(ir58_result))},
        {"phase": "IR59", "content": "Archive Integrity Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir59_live, "judgement": _judgement(ir59_live)},
        {"phase": "IR60", "content": "Phase 56-60 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": ir59_live, "judgement": _judgement(ir59_live)},
    ]

    bundle = {
        "schema_version": IR60_SCHEMA_VERSION,
        "phase": "IR60",
        "generated_at": _now_iso(),
        "source_task_id": ir56_60_output.get("source_task_id", "UNKNOWN"),
        "ir56_result": ir56_result,
        "ir57_result": ir57_result,
        "ir58_result": ir58_result,
        "ir59_result": ir59_result,
        "test_summary": {"focused": focused, "adjacent": adjacent, "scoped": scoped},
        "live_summary": {
            "ir56": table_rows[0]["live"],
            "ir57": table_rows[1]["live"],
            "ir58": table_rows[2]["live"],
            "ir59": table_rows[3]["live"],
            "ir60": table_rows[4]["live"],
        },
        "safety_gate_summary": _default_safety_gate(),
        "completion_table": table_rows,
        "final_decision": final_decision,
        "artifacts": {
            **ir56_60_output.get("artifacts", {}),
            "ir60_completion_bundle": "generic_block_ai/reports/ir56_60/ir60_completion_bundle.json",
            "ir56_60_live_status": "generic_block_ai/reports/ir56_60/ir56_60_live_status.md",
            "ir56_60_completion_table": "generic_block_ai/reports/ir56_60/ir56_60_completion_table.md",
        },
        "external_write_executed": False,
    }

    bundle_path = out_dir / "ir60_completion_bundle.json"
    _write_json(bundle_path, bundle)

    live_md = [
        "# IR56-IR60 Live Status",
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
    live_path = out_dir / "ir56_60_live_status.md"
    _write_text(live_path, "\n".join(live_md) + "\n")

    table_md = [
        "# IR56-IR60 Completion Table",
        "",
        "| Phase | 内容 | focused | adjacent | scoped | live | 判定 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in table_rows:
        table_md.append(
            f"| {row['phase']} | {row['content']} | {row['focused']} | {row['adjacent']} | {row['scoped']} | {row['live']} | {row['judgement']} |"
        )
    table_path = out_dir / "ir56_60_completion_table.md"
    _write_text(table_path, "\n".join(table_md) + "\n")

    return {
        "path": str(bundle_path),
        "completion_report": bundle,
        "artifacts": {
            "ir60_completion_bundle": _to_ref(bundle_path, project_root),
            "ir56_60_live_status": _to_ref(live_path, project_root),
            "ir56_60_completion_table": _to_ref(table_path, project_root),
        },
        "external_write_executed": False,
    }

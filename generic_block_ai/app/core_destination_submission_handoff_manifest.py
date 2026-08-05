"""
core_destination_submission_handoff_manifest.py - IR50

Build destination submission handoff manifests from IR49 submission readiness in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR49_SCHEMA_VERSION = "ir49_destination_submission_readiness_gate_v1"
IR50_SCHEMA_VERSION = "ir50_destination_submission_handoff_manifest_v1"

READINESS_READY = "READY_DRY_RUN_ONLY"
READINESS_HOLD = "HOLD"
READINESS_REJECT = "REJECT"
READINESS_ABORT = "ABORT"

HANDOFF_INCLUDE = "INCLUDE_IN_DRY_RUN_HANDOFF"
HANDOFF_HOLD = "HOLD"
HANDOFF_REJECT = "REJECT"
HANDOFF_ABORT = "ABORT"

OVERALL_HANDOFF_READY = "READY_DRY_RUN_HANDOFF"
OVERALL_HANDOFF_HOLD = "HOLD"
OVERALL_HANDOFF_REJECT = "REJECT"
OVERALL_HANDOFF_ABORT = "ABORT"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _handoff_decision(row: dict[str, Any]) -> tuple[str, list[str]]:
    readiness = str(row.get("submission_readiness_decision", "UNKNOWN"))
    reasons = [str(v) for v in row.get("readiness_reasons", [])]

    if readiness == READINESS_READY:
        return HANDOFF_INCLUDE, ["destination included in dry-run handoff manifest"]
    if readiness == READINESS_HOLD:
        return HANDOFF_HOLD, reasons or ["destination withheld from handoff until hold is cleared"]
    if readiness == READINESS_REJECT:
        return HANDOFF_REJECT, reasons or ["destination excluded from handoff due to rejection"]
    return HANDOFF_ABORT, reasons or ["destination excluded from handoff due to abort state"]


def _overall_handoff(decisions: list[str]) -> str:
    if HANDOFF_ABORT in decisions:
        return OVERALL_HANDOFF_ABORT
    if HANDOFF_REJECT in decisions:
        return OVERALL_HANDOFF_REJECT
    if HANDOFF_HOLD in decisions:
        return OVERALL_HANDOFF_HOLD
    return OVERALL_HANDOFF_READY


def run_ir50_destination_submission_handoff_manifest_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir49_submission_readiness_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR50-T1/T2/T3/T4
    Convert IR49 submission readiness outputs into dry-run submission handoff manifests.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir49_path = ir49_submission_readiness_report_path or (
        reports_dir / "ir49_destination_submission_readiness_gate_report_ir49_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_handoff_manifest: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"
    overall_submission_gate_decision = "UNKNOWN"
    overall_review_queue_approval_decision = "UNKNOWN"
    overall_human_review_result = "UNKNOWN"
    overall_submission_readiness_decision = "UNKNOWN"

    if not ir49_path.exists():
        failed_checks.append(f"ir49 submission readiness report not found: {ir49_path}")

    ir49_report: dict[str, Any] = {}
    if not failed_checks:
        ir49_report = _read_json(ir49_path)
        if ir49_report.get("schema_version") != IR49_SCHEMA_VERSION:
            failed_checks.append(f"ir49 schema_version must be {IR49_SCHEMA_VERSION}")

        release_candidate_id = str(ir49_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir49_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir49_report.get("overall_approval_decision", "UNKNOWN"))
        overall_submission_gate_decision = str(ir49_report.get("overall_submission_gate_decision", "UNKNOWN"))
        overall_review_queue_approval_decision = str(
            ir49_report.get("overall_review_queue_approval_decision", "UNKNOWN")
        )
        overall_human_review_result = str(ir49_report.get("overall_human_review_result", "UNKNOWN"))
        overall_submission_readiness_decision = str(
            ir49_report.get("overall_submission_readiness_decision", "UNKNOWN")
        )

    rows = ir49_report.get("destination_submission_readiness", [])
    if not isinstance(rows, list):
        failed_checks.append("ir49 destination_submission_readiness must be list")
        rows = []

    manifest_root = reports_dir / f"ir50_destination_submission_handoff_manifest_{_safe(source_task_id)}"
    manifest_root.mkdir(parents=True, exist_ok=True)

    handoff_targets: list[str] = []
    handoff_reference_paths: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir49 destination_submission_readiness entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        handoff_decision, handoff_reasons = _handoff_decision(row)
        if handoff_decision == HANDOFF_INCLUDE:
            handoff_targets.append(destination)

        intake_record_path = str(row.get("intake_record_path", ""))
        if intake_record_path:
            handoff_reference_paths.append(intake_record_path)

        destination_handoff_manifest.append(
            {
                "destination": destination,
                "handoff_manifest_decision": handoff_decision,
                "submission_readiness_decision": str(row.get("submission_readiness_decision", "UNKNOWN")),
                "handoff_reasons": handoff_reasons,
                "reviewer_role": str(row.get("reviewer_role", "UNKNOWN")),
                "review_item_ids": [str(v) for v in row.get("review_item_ids", [])],
                "review_notes": [str(v) for v in row.get("review_notes", [])],
                "intake_record_path": intake_record_path,
                "evidence_reference_links": row.get("evidence_reference_links", {}),
            }
        )

    decisions = [r["handoff_manifest_decision"] for r in destination_handoff_manifest]
    overall_submission_handoff_decision = _overall_handoff(decisions)

    include_count = sum(1 for d in decisions if d == HANDOFF_INCLUDE)
    hold_count = sum(1 for d in decisions if d == HANDOFF_HOLD)
    reject_count = sum(1 for d in decisions if d == HANDOFF_REJECT)
    abort_count = sum(1 for d in decisions if d == HANDOFF_ABORT)

    if overall_submission_readiness_decision == "UNKNOWN":
        failed_checks.append("overall_submission_readiness_decision is missing or unknown")

    if overall_submission_handoff_decision == OVERALL_HANDOFF_READY:
        overall_handoff_action = "Dry-run submission handoff manifest is ready without executing submission."
    elif overall_submission_handoff_decision == OVERALL_HANDOFF_HOLD:
        overall_handoff_action = "Handoff manifest recorded, but held destinations block dry-run progression."
    elif overall_submission_handoff_decision == OVERALL_HANDOFF_REJECT:
        overall_handoff_action = "Handoff manifest recorded rejected destinations and prevents progression."
    else:
        overall_handoff_action = "Handoff manifest recorded abort conditions and prevents progression."

    manifest_json_path = manifest_root / "destination_submission_handoff_manifest.json"
    summary_md_path = manifest_root / "destination_submission_handoff_manifest_summary.md"

    report = {
        "schema_version": IR50_SCHEMA_VERSION,
        "phase": "IR50",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_review_queue_approval_decision": overall_review_queue_approval_decision,
        "overall_human_review_result": overall_human_review_result,
        "overall_submission_readiness_decision": overall_submission_readiness_decision,
        "overall_submission_handoff_decision": overall_submission_handoff_decision,
        "overall_handoff_action": overall_handoff_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_handoff_manifest),
            "include_in_dry_run_handoff_count": include_count,
            "hold_count": hold_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
            "handoff_target_count": len(handoff_targets),
        },
        "handoff_manifest": {
            "target_destinations": handoff_targets,
            "reference_record_paths": handoff_reference_paths,
            "submission_execution_blocked": True,
            "network_transmission_blocked": True,
            "production_release_blocked": True,
        },
        "destination_submission_handoff_manifest": destination_handoff_manifest,
        "artifacts": {
            "manifest_root": _to_ref(manifest_root, project_root),
            "destination_submission_handoff_manifest": _to_ref(manifest_json_path, project_root),
            "destination_submission_handoff_manifest_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase50_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "submission_execution_blocked": True,
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    manifest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Submission Handoff Manifest",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Submission Handoff Decision: {overall_submission_handoff_decision}",
        f"- Overall Handoff Action: {overall_handoff_action}",
        "",
        "## Handoff Targets",
    ]
    for destination in handoff_targets:
        summary_lines.append(f"- {destination}")
    summary_lines.append("")
    summary_lines.append("## Destination Handoff Decisions")
    for row in destination_handoff_manifest:
        summary_lines.append(f"- {row['destination']} -> {row['handoff_manifest_decision']}")
        for reason in row.get("handoff_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir50_destination_submission_handoff_manifest_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir50_completion_report(
    *,
    base_path: Path,
    ir50_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR50-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir50_output.get("runbook_report", {}) if isinstance(ir50_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 50",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR50_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir48_ir50": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_review_queue_approval_decision": runbook.get("overall_review_queue_approval_decision", "UNKNOWN"),
        "overall_human_review_result": runbook.get("overall_human_review_result", "UNKNOWN"),
        "overall_submission_readiness_decision": runbook.get("overall_submission_readiness_decision", "UNKNOWN"),
        "overall_submission_handoff_decision": runbook.get("overall_submission_handoff_decision", "UNKNOWN"),
        "overall_handoff_action": runbook.get("overall_handoff_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir50_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase50_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "submission_execution_blocked": True,
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase50_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
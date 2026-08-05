"""
core_destination_evidence_bundle_submission_gate.py - IR44

Gate destination evidence bundles into submission decisions from IR43 verifier
results in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR43_SCHEMA_VERSION = "ir43_destination_evidence_bundle_verifier_v1"
IR44_SCHEMA_VERSION = "ir44_destination_evidence_bundle_submission_gate_v1"

DECISION_READY_FOR_REVIEW = "READY_FOR_REVIEW"
DECISION_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"


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


def _destination_decision(row: dict[str, Any]) -> tuple[str, list[str]]:
    checks = row.get("verification_checks", {}) if isinstance(row.get("verification_checks"), dict) else {}
    reasons: list[str] = []

    hash_manifest_exists = bool(checks.get("hash_manifest_exists", False))
    summary_exists = bool(checks.get("summary_exists", False))
    manifest_hash_ok = bool(checks.get("manifest_hash_ok", False))
    recompute_ok = bool(checks.get("recompute_ok", False))
    summary_ok = bool(checks.get("summary_ok", False))
    completeness_ok = bool(checks.get("completeness_ok", False))

    if not hash_manifest_exists or not summary_exists:
        reasons.append("critical evidence artifact missing")
        return DECISION_ABORT, reasons

    if not manifest_hash_ok or not summary_ok:
        reasons.append("evidence integrity mismatch detected")
        return DECISION_REJECT, reasons

    if not completeness_ok or not recompute_ok:
        reasons.append("manual review required for evidence consistency")
        return DECISION_HUMAN_REVIEW_REQUIRED, reasons

    reasons.append("bundle verification checks passed")
    return DECISION_READY_FOR_REVIEW, reasons


def _overall_decision(decisions: list[str]) -> str:
    if DECISION_ABORT in decisions:
        return DECISION_ABORT
    if DECISION_REJECT in decisions:
        return DECISION_REJECT
    if DECISION_HUMAN_REVIEW_REQUIRED in decisions:
        return DECISION_HUMAN_REVIEW_REQUIRED
    return DECISION_READY_FOR_REVIEW


def run_ir44_destination_evidence_bundle_submission_gate_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir43_verifier_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR44-T1/T2/T3/T4
    Convert IR43 destination verification into submission-gate decisions.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir43_path = ir43_verifier_report_path or (
        reports_dir / "ir43_destination_evidence_bundle_verifier_report_ir43_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_gate_results: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir43_path.exists():
        failed_checks.append(f"ir43 verifier report not found: {ir43_path}")

    ir43_report: dict[str, Any] = {}
    if not failed_checks:
        ir43_report = _read_json(ir43_path)
        if ir43_report.get("schema_version") != IR43_SCHEMA_VERSION:
            failed_checks.append(f"ir43 schema_version must be {IR43_SCHEMA_VERSION}")

        release_candidate_id = str(ir43_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir43_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir43_report.get("overall_approval_decision", "UNKNOWN"))

    rows = ir43_report.get("destination_evidence_bundle_verification", [])
    if not isinstance(rows, list):
        failed_checks.append("ir43 destination_evidence_bundle_verification must be list")
        rows = []

    for row in rows:
        if not isinstance(row, dict):
            failed_checks.append("ir43 destination_evidence_bundle_verification entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision, reasons = _destination_decision(row)
        destination_gate_results.append(
            {
                "destination": destination,
                "submission_gate_decision": decision,
                "gate_reasons": reasons,
                "verification_status": str(row.get("verification_status", "UNKNOWN")),
                "verification_checks": row.get("verification_checks", {}),
                "bundle_hash": str(row.get("bundle_hash", "")),
                "evidence_digest": str(row.get("evidence_digest", "")),
                "hash_manifest_path": str(row.get("hash_manifest_path", "")),
                "review_summary_path": str(row.get("review_summary_path", "")),
            }
        )

    decisions = [r["submission_gate_decision"] for r in destination_gate_results]
    overall_submission_gate_decision = _overall_decision(decisions)

    ready_count = sum(1 for d in decisions if d == DECISION_READY_FOR_REVIEW)
    human_review_count = sum(1 for d in decisions if d == DECISION_HUMAN_REVIEW_REQUIRED)
    reject_count = sum(1 for d in decisions if d == DECISION_REJECT)
    abort_count = sum(1 for d in decisions if d == DECISION_ABORT)

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")

    overall_gate_action = {
        DECISION_READY_FOR_REVIEW: "All destinations are ready for human review handoff.",
        DECISION_HUMAN_REVIEW_REQUIRED: "Hold for manual review before submission readiness.",
        DECISION_REJECT: "Reject affected destinations and require evidence correction.",
        DECISION_ABORT: "Abort gate due to critical missing evidence artifacts.",
    }.get(overall_submission_gate_decision, "Unknown decision; enforce safe hold.")

    gate_root = reports_dir / f"ir44_destination_evidence_bundle_submission_gate_{_safe(source_task_id)}"
    gate_root.mkdir(parents=True, exist_ok=True)

    gate_json_path = gate_root / "destination_evidence_bundle_submission_gate.json"
    summary_md_path = gate_root / "destination_evidence_bundle_submission_gate_summary.md"

    report = {
        "schema_version": IR44_SCHEMA_VERSION,
        "phase": "IR44",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_submission_gate_decision": overall_submission_gate_decision,
        "overall_gate_action": overall_gate_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_gate_results),
            "ready_for_review_count": ready_count,
            "human_review_required_count": human_review_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
        },
        "destination_submission_gate": destination_gate_results,
        "artifacts": {
            "gate_root": _to_ref(gate_root, project_root),
            "destination_evidence_bundle_submission_gate": _to_ref(gate_json_path, project_root),
            "destination_evidence_bundle_submission_gate_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase44_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    gate_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# Destination Evidence Bundle Submission Gate",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Submission Gate Decision: {overall_submission_gate_decision}",
        f"- Overall Gate Action: {overall_gate_action}",
        "",
        "## Destination Gate Decisions",
    ]
    for row in destination_gate_results:
        summary_lines.append(f"- {row['destination']} -> {row['submission_gate_decision']}")
        for reason in row.get("gate_reasons", []):
            summary_lines.append(f"  - {reason}")
    summary_md_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir44_destination_evidence_bundle_submission_gate_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir44_completion_report(
    *,
    base_path: Path,
    ir44_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR44-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir44_output.get("runbook_report", {}) if isinstance(ir44_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 44",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR44_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir42_ir44": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_submission_gate_decision": runbook.get("overall_submission_gate_decision", "UNKNOWN"),
        "overall_gate_action": runbook.get("overall_gate_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir44_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase44_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase44_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
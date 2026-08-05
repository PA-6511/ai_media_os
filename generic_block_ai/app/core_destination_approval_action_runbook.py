"""
core_destination_approval_action_runbook.py - IR37

Generate destination-specific approval action runbook from IR36
Destination Approval Gate Matrix in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR36_SCHEMA_VERSION = "ir36_destination_approval_gate_matrix_v1"
IR37_SCHEMA_VERSION = "ir37_destination_approval_action_runbook_v1"

DECISION_APPROVE_DRY_RUN = "APPROVE_DRY_RUN"
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


def _infer_resubmission_patterns(reasons: list[str]) -> list[str]:
    text = "\n".join(reasons).lower()
    patterns: list[str] = []
    if "required" in text or "missing" in text:
        patterns.append("R1")
    if "forbidden" in text or "unexpected" in text:
        patterns.append("R2")
    if "signature" in text:
        patterns.append("R3")
    if "attachment" in text or "json" in text:
        patterns.append("R4")
    if not patterns:
        patterns.append("R1")
    return sorted(set(patterns))


def _build_action_plan(decision: str, reasons: list[str], warnings: list[str]) -> dict[str, Any]:
    if decision == DECISION_APPROVE_DRY_RUN:
        return {
            "requires_human_review": False,
            "requires_resubmission": False,
            "resubmission_patterns": [],
            "actions": [
                "Keep operation mode in dry_run and OBSERVE.",
                "Prepare destination package checklist for human signoff.",
                "Do not execute any external submission or network transmission.",
            ],
            "escalation": "none",
        }

    if decision == DECISION_HUMAN_REVIEW_REQUIRED:
        return {
            "requires_human_review": True,
            "requires_resubmission": False,
            "resubmission_patterns": [],
            "human_review_conditions": reasons + warnings,
            "actions": [
                "Queue destination for human review with evidence package.",
                "Resolve warnings before next gate execution.",
                "Re-run IR36 decision after reviewer decision is recorded.",
            ],
            "escalation": "human_reviewer",
        }

    if decision == DECISION_REJECT:
        return {
            "requires_human_review": True,
            "requires_resubmission": True,
            "resubmission_patterns": _infer_resubmission_patterns(reasons),
            "actions": [
                "Reject current destination package and stop progression for this destination.",
                "Apply mapped resubmission patterns and rebuild package artifacts.",
                "Run IR35 then IR36 again before any approval consideration.",
            ],
            "escalation": "package_owner_and_reviewer",
        }

    # ABORT or unknown defaults to ABORT-grade runbook.
    return {
        "requires_human_review": True,
        "requires_resubmission": True,
        "resubmission_patterns": ["R1", "R2", "R3", "R4"],
        "actions": [
            "Abort destination flow and preserve audit evidence immediately.",
            "Enforce no-go lock: no external write, no network transmission, no production release.",
            "Open incident review and require explicit human unlock decision before retry.",
        ],
        "escalation": "incident_commander",
    }


def run_ir37_destination_approval_action_runbook_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir36_approval_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR37-T1/T2/T3/T4
    Generate destination-level action runbook from IR36 approval report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir36_path = ir36_approval_report_path or (
        reports_dir / "ir36_destination_approval_gate_matrix_report_ir36_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_runbooks: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir36_path.exists():
        failed_checks.append(f"ir36 approval report not found: {ir36_path}")

    ir36_report: dict[str, Any] = {}
    if not failed_checks:
        ir36_report = _read_json(ir36_path)
        if ir36_report.get("schema_version") != IR36_SCHEMA_VERSION:
            failed_checks.append(f"ir36 schema_version must be {IR36_SCHEMA_VERSION}")

        release_candidate_id = str(ir36_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir36_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir36_report.get("overall_approval_decision", "UNKNOWN"))

    decisions = ir36_report.get("decisions", []) if isinstance(ir36_report.get("decisions"), list) else []

    for row in decisions:
        if not isinstance(row, dict):
            failed_checks.append("ir36 decisions entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision = str(row.get("approval_decision", "UNKNOWN"))
        reasons = [str(v) for v in row.get("reasons", [])]
        row_warnings = [str(v) for v in row.get("warnings", [])]

        plan = _build_action_plan(decision, reasons, row_warnings)
        destination_runbooks.append(
            {
                "destination": destination,
                "approval_decision": decision,
                "source_reasons": reasons,
                "source_warnings": row_warnings,
                **plan,
                "manifest_path": str(row.get("manifest_path", "")),
            }
        )

    approve_count = sum(1 for d in destination_runbooks if d["approval_decision"] == DECISION_APPROVE_DRY_RUN)
    review_count = sum(1 for d in destination_runbooks if d["approval_decision"] == DECISION_HUMAN_REVIEW_REQUIRED)
    reject_count = sum(1 for d in destination_runbooks if d["approval_decision"] == DECISION_REJECT)
    abort_count = sum(1 for d in destination_runbooks if d["approval_decision"] == DECISION_ABORT)

    overall_action = {
        DECISION_APPROVE_DRY_RUN: "Proceed as dry-run only; keep external submission blocked.",
        DECISION_HUMAN_REVIEW_REQUIRED: "Hold and execute human review workflow before retry.",
        DECISION_REJECT: "Reject current release package and trigger resubmission process.",
        DECISION_ABORT: "Abort flow, preserve evidence, and require incident-level human unlock.",
    }.get(overall_approval_decision, "Unknown overall decision; force safe hold and human review.")

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")

    if reject_count > 0 and review_count == 0:
        warnings.append("reject destinations present without explicit human_review_required destinations")

    runbook_root = reports_dir / f"ir37_destination_approval_action_runbook_{_safe(source_task_id)}"
    runbook_root.mkdir(parents=True, exist_ok=True)

    runbook_json_path = runbook_root / "destination_action_runbook.json"
    summary_md_path = runbook_root / "destination_action_summary.md"

    report = {
        "schema_version": IR37_SCHEMA_VERSION,
        "phase": "IR37",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_action": overall_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_runbooks),
            "approve_dry_run_count": approve_count,
            "human_review_required_count": review_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
        },
        "destination_actions": destination_runbooks,
        "artifacts": {
            "runbook_root": _to_ref(runbook_root, project_root),
            "destination_action_runbook": _to_ref(runbook_json_path, project_root),
            "destination_action_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase37_completion_report.json",
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

    runbook_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Destination Approval Action Runbook",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Action: {overall_action}",
        "",
        "## Destination Actions",
    ]
    for row in destination_runbooks:
        md_lines.append(f"- {row['destination']} -> {row['approval_decision']}")
        for action in row.get("actions", []):
            md_lines.append(f"  - {action}")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir37_destination_approval_action_runbook_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir37_completion_report(
    *,
    base_path: Path,
    ir37_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR37-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir37_output.get("runbook_report", {}) if isinstance(ir37_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 37",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR37_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir35_ir37": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_action": runbook.get("overall_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir37_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase37_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase37_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

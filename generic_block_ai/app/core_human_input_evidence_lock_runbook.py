"""
core_human_input_evidence_lock_runbook.py - IR38

Generate human input and evidence lock runbook from IR37 destination action runbook
in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR37_SCHEMA_VERSION = "ir37_destination_approval_action_runbook_v1"
IR38_SCHEMA_VERSION = "ir38_human_input_evidence_lock_runbook_v1"

DECISION_APPROVE_DRY_RUN = "APPROVE_DRY_RUN"
DECISION_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"

BASE_APPROVER_RECORD_FIELDS = [
    "approver_id",
    "approver_role",
    "approval_action",
    "approval_timestamp_utc",
    "approval_comment",
]


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


def _human_input_format(decision: str) -> dict[str, Any]:
    fields = list(BASE_APPROVER_RECORD_FIELDS)
    options = ["approve", "request_fix", "reject", "abort"]

    if decision == DECISION_APPROVE_DRY_RUN:
        options = ["approve", "request_fix"]
    elif decision == DECISION_HUMAN_REVIEW_REQUIRED:
        fields.append("review_findings")
        fields.append("required_followup_actions")
        options = ["approve", "request_fix", "reject"]
    elif decision == DECISION_REJECT:
        fields.append("rejection_reason")
        fields.append("required_resubmission_pattern_ids")
        options = ["request_fix", "reject", "abort"]
    elif decision == DECISION_ABORT:
        fields.append("incident_ticket_id")
        fields.append("abort_reason")
        options = ["abort"]
    else:
        fields.append("unknown_decision_reason")

    return {
        "required_fields": fields,
        "allowed_actions": options,
        "input_format": "json_record",
    }


def _evidence_lock_steps(decision: str) -> list[str]:
    base = [
        "Freeze destination decision record and approver input snapshot.",
        "Store immutable digest for runbook payload and destination manifest refs.",
        "Persist lock timestamp and operator metadata in audit trail.",
    ]

    if decision == DECISION_REJECT:
        base.append("Lock rejected package revision and open resubmission-only branch.")
    if decision == DECISION_ABORT:
        base.append("Activate no-go lock and incident evidence preservation mode.")
        base.append("Block any unlock until incident commander approval is recorded.")

    return base


def _return_or_abort_lock_steps(decision: str) -> list[str]:
    if decision == DECISION_ABORT:
        return [
            "Abort path: keep no-go lock enabled.",
            "Record incident ticket linkage and response owner.",
            "Require explicit human unlock event before re-entry.",
        ]

    if decision == DECISION_REJECT:
        return [
            "Return path: mark destination as REJECTED.",
            "Allow only resubmission artifact updates.",
            "Re-run IR35->IR37->IR38 after correction.",
        ]

    if decision == DECISION_HUMAN_REVIEW_REQUIRED:
        return [
            "Return path: keep destination in review queue.",
            "Collect reviewer findings and rerun gate after update.",
        ]

    return [
        "No return path triggered; keep dry-run approvals locked until next phase handoff.",
    ]


def run_ir38_human_input_evidence_lock_runbook_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir37_runbook_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR38-T1/T2/T3/T4
    Generate human input & evidence lock runbook from IR37 report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir37_path = ir37_runbook_report_path or (
        reports_dir / "ir37_destination_approval_action_runbook_report_ir37_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_human_lock_runbooks: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    overall_approval_decision = "UNKNOWN"

    if not ir37_path.exists():
        failed_checks.append(f"ir37 runbook report not found: {ir37_path}")

    ir37_report: dict[str, Any] = {}
    if not failed_checks:
        ir37_report = _read_json(ir37_path)
        if ir37_report.get("schema_version") != IR37_SCHEMA_VERSION:
            failed_checks.append(f"ir37 schema_version must be {IR37_SCHEMA_VERSION}")

        release_candidate_id = str(ir37_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir37_report.get("final_submission_decision", "UNKNOWN"))
        overall_approval_decision = str(ir37_report.get("overall_approval_decision", "UNKNOWN"))

    destination_actions = (
        ir37_report.get("destination_actions", [])
        if isinstance(ir37_report.get("destination_actions"), list)
        else []
    )

    for row in destination_actions:
        if not isinstance(row, dict):
            failed_checks.append("ir37 destination_actions entry must be object")
            continue

        destination = str(row.get("destination", "UNKNOWN"))
        decision = str(row.get("approval_decision", "UNKNOWN"))
        source_reasons = [str(v) for v in row.get("source_reasons", [])]
        source_warnings = [str(v) for v in row.get("source_warnings", [])]

        human_input = _human_input_format(decision)
        lock_steps = _evidence_lock_steps(decision)
        return_steps = _return_or_abort_lock_steps(decision)

        destination_human_lock_runbooks.append(
            {
                "destination": destination,
                "approval_decision": decision,
                "human_input": human_input,
                "approver_record_required": True,
                "evidence_lock_steps": lock_steps,
                "return_or_abort_lock_steps": return_steps,
                "source_reasons": source_reasons,
                "source_warnings": source_warnings,
                "manifest_path": str(row.get("manifest_path", "")),
            }
        )

    approve_count = sum(1 for d in destination_human_lock_runbooks if d["approval_decision"] == DECISION_APPROVE_DRY_RUN)
    review_count = sum(1 for d in destination_human_lock_runbooks if d["approval_decision"] == DECISION_HUMAN_REVIEW_REQUIRED)
    reject_count = sum(1 for d in destination_human_lock_runbooks if d["approval_decision"] == DECISION_REJECT)
    abort_count = sum(1 for d in destination_human_lock_runbooks if d["approval_decision"] == DECISION_ABORT)

    if overall_approval_decision == "UNKNOWN":
        failed_checks.append("overall_approval_decision is missing or unknown")

    overall_runbook_action = {
        DECISION_APPROVE_DRY_RUN: "Collect approver records and lock evidence for dry-run approval path.",
        DECISION_HUMAN_REVIEW_REQUIRED: "Collect reviewer input and lock review evidence before retry.",
        DECISION_REJECT: "Collect rejection records and lock for resubmission-only handling.",
        DECISION_ABORT: "Collect incident input and enforce strict evidence lock under no-go.",
    }.get(overall_approval_decision, "Unknown overall decision; hold with mandatory human review and evidence lock.")

    runbook_root = reports_dir / f"ir38_human_input_evidence_lock_runbook_{_safe(source_task_id)}"
    runbook_root.mkdir(parents=True, exist_ok=True)

    runbook_json_path = runbook_root / "destination_human_input_evidence_lock_runbook.json"
    summary_md_path = runbook_root / "destination_human_input_evidence_lock_summary.md"

    report = {
        "schema_version": IR38_SCHEMA_VERSION,
        "phase": "IR38",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "overall_approval_decision": overall_approval_decision,
        "overall_runbook_action": overall_runbook_action,
        "validation_result": "FAIL" if failed_checks else ("WARN" if warnings else "PASS"),
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_human_lock_runbooks),
            "approve_dry_run_count": approve_count,
            "human_review_required_count": review_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
            "approver_record_required_count": len(destination_human_lock_runbooks),
        },
        "destination_human_input_evidence_lock": destination_human_lock_runbooks,
        "artifacts": {
            "runbook_root": _to_ref(runbook_root, project_root),
            "destination_human_input_evidence_lock_runbook": _to_ref(runbook_json_path, project_root),
            "destination_human_input_evidence_lock_summary": _to_ref(summary_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase38_completion_report.json",
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
        "# Human Input & Evidence Lock Runbook",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Overall Approval Decision: {overall_approval_decision}",
        f"- Overall Runbook Action: {overall_runbook_action}",
        "",
        "## Destination Human Input & Lock Steps",
    ]
    for row in destination_human_lock_runbooks:
        md_lines.append(f"- {row['destination']} -> {row['approval_decision']}")
        for step in row.get("evidence_lock_steps", []):
            md_lines.append(f"  - {step}")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir38_human_input_evidence_lock_runbook_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "runbook_report": report,
        "external_write_executed": False,
    }


def write_ir38_completion_report(
    *,
    base_path: Path,
    ir38_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR38-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    runbook = ir38_output.get("runbook_report", {}) if isinstance(ir38_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 38",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR38_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir36_ir38": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": runbook.get("overall_approval_decision", "UNKNOWN"),
        "overall_runbook_action": runbook.get("overall_runbook_action", "UNKNOWN"),
        "release_candidate_id": runbook.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": runbook.get("final_submission_decision", "UNKNOWN"),
        "validation_result": runbook.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(runbook.get("validation_failed_checks", [])),
        "validation_warning_count": len(runbook.get("validation_warnings", [])),
        "summary": runbook.get("summary", {}),
        "artifacts": {
            "runbook_report": ir38_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase38_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase38_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

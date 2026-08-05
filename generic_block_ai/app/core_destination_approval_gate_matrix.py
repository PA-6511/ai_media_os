"""
core_destination_approval_gate_matrix.py - IR36

Convert IR35 destination validation matrix into approval gate decisions
per destination in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR35_SCHEMA_VERSION = "ir35_destination_package_validation_matrix_v1"
IR36_SCHEMA_VERSION = "ir36_destination_approval_gate_matrix_v1"

DECISION_APPROVE_DRY_RUN = "APPROVE_DRY_RUN"
DECISION_HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"


SENSITIVE_FAIL_KEYWORDS = {
    "external",
    "network",
    "execution_policy_execute",
    "forbidden",
    "tamper",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _resolve(project_root: Path, value: str) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return project_root / p


def _to_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _has_sensitive_failure(reasons: list[str]) -> bool:
    lowered = "\n".join(reasons).lower()
    return any(keyword in lowered for keyword in SENSITIVE_FAIL_KEYWORDS)


def _destination_decision(destination_result: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    source_result = str(destination_result.get("validation_result", "FAIL")).upper()
    failed_checks = [str(v) for v in destination_result.get("failed_checks", [])]
    warnings = [str(v) for v in destination_result.get("warnings", [])]

    if source_result == "FAIL":
        if _has_sensitive_failure(failed_checks):
            return DECISION_ABORT, failed_checks, warnings
        return DECISION_REJECT, failed_checks, warnings
    if source_result == "WARN":
        return DECISION_HUMAN_REVIEW_REQUIRED, failed_checks, warnings
    if source_result == "PASS":
        return DECISION_APPROVE_DRY_RUN, failed_checks, warnings

    return DECISION_REJECT, failed_checks + [f"unknown validation_result: {source_result}"], warnings


def run_ir36_destination_approval_gate_matrix_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir35_validation_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR36-T1/T2/T3/T4
    Build destination approval gate matrix from IR35 validation report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir35_path = ir35_validation_report_path or (
        reports_dir / "ir35_destination_package_validation_matrix_report_ir35_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    decisions: list[dict[str, Any]] = []
    global_abort_reasons: list[str] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    source_validation_result = "UNKNOWN"

    if not ir35_path.exists():
        failed_checks.append(f"ir35 validation report not found: {ir35_path}")

    ir35_report: dict[str, Any] = {}
    if not failed_checks:
        ir35_report = _read_json(ir35_path)
        if ir35_report.get("schema_version") != IR35_SCHEMA_VERSION:
            failed_checks.append(f"ir35 schema_version must be {IR35_SCHEMA_VERSION}")

        release_candidate_id = str(ir35_report.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir35_report.get("final_submission_decision", "UNKNOWN"))
        source_validation_result = str(ir35_report.get("validation_result", "UNKNOWN"))

    safeguards = ir35_report.get("safeguards", {}) if isinstance(ir35_report.get("safeguards"), dict) else {}
    execution_policy_execute = bool(safeguards.get("execution_policy_execute", False))
    external_write_executed = bool(safeguards.get("external_write_executed", False))
    network_transmission_executed = bool(safeguards.get("network_transmission_executed", False))

    if execution_policy_execute:
        global_abort_reasons.append("execution_policy_execute must remain false")
    if external_write_executed:
        global_abort_reasons.append("external_write_executed must remain false")
    if network_transmission_executed:
        global_abort_reasons.append("network_transmission_executed must remain false")

    matrix = ir35_report.get("matrix", {}) if isinstance(ir35_report.get("matrix"), dict) else {}
    global_checks = matrix.get("global_checks", {}) if isinstance(matrix.get("global_checks"), dict) else {}
    if global_checks and not bool(global_checks.get("required_resubmission_patterns_present", False)):
        global_abort_reasons.append("required resubmission patterns are missing")

    destinations = matrix.get("destinations", []) if isinstance(matrix.get("destinations"), list) else []

    for destination_result in destinations:
        if not isinstance(destination_result, dict):
            failed_checks.append("destination matrix entry must be object")
            continue

        decision, reasons, decision_warnings = _destination_decision(destination_result)
        decisions.append(
            {
                "destination": str(destination_result.get("destination", "UNKNOWN")),
                "approval_decision": decision,
                "reasons": reasons,
                "warnings": decision_warnings,
                "source_validation_result": str(destination_result.get("validation_result", "UNKNOWN")),
                "manifest_path": str(destination_result.get("manifest_path", "")),
            }
        )

    for row in decisions:
        for reason in row.get("reasons", []):
            if isinstance(reason, str) and reason:
                failed_checks.append(f"{row.get('destination')}: {reason}")
        for warning in row.get("warnings", []):
            if isinstance(warning, str) and warning:
                warnings.append(f"{row.get('destination')}: {warning}")

    approve_count = sum(1 for d in decisions if d["approval_decision"] == DECISION_APPROVE_DRY_RUN)
    review_count = sum(1 for d in decisions if d["approval_decision"] == DECISION_HUMAN_REVIEW_REQUIRED)
    reject_count = sum(1 for d in decisions if d["approval_decision"] == DECISION_REJECT)
    abort_count = sum(1 for d in decisions if d["approval_decision"] == DECISION_ABORT)

    global_abort = bool(global_abort_reasons)
    if global_abort:
        overall_approval_decision = DECISION_ABORT
    elif abort_count > 0:
        overall_approval_decision = DECISION_ABORT
    elif reject_count > 0:
        overall_approval_decision = DECISION_REJECT
    elif review_count > 0 or source_validation_result == "WARN" or warnings:
        overall_approval_decision = DECISION_HUMAN_REVIEW_REQUIRED
    elif source_validation_result == "PASS" and approve_count == len(decisions):
        overall_approval_decision = DECISION_APPROVE_DRY_RUN
    else:
        overall_approval_decision = DECISION_REJECT

    matrix_root = reports_dir / f"ir36_destination_approval_gate_matrix_{_safe(source_task_id)}"
    matrix_root.mkdir(parents=True, exist_ok=True)

    matrix_json_path = matrix_root / "destination_approval_gate_matrix.json"
    summary_json_path = matrix_root / "destination_approval_summary.json"

    report = {
        "schema_version": IR36_SCHEMA_VERSION,
        "phase": "IR36",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "source_validation_result": source_validation_result,
        "overall_approval_decision": overall_approval_decision,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(decisions),
            "approve_dry_run_count": approve_count,
            "human_review_required_count": review_count,
            "reject_count": reject_count,
            "abort_count": abort_count,
            "global_abort": global_abort,
        },
        "decisions": decisions,
        "artifacts": {
            "matrix_root": _to_ref(matrix_root, project_root),
            "destination_approval_gate_matrix": _to_ref(matrix_json_path, project_root),
            "destination_approval_summary": _to_ref(summary_json_path, project_root),
            "completion_report": "reports/implementation_restart_phase36_completion_report.json",
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

    matrix_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema_version": IR36_SCHEMA_VERSION,
        "phase": "IR36",
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "overall_approval_decision": overall_approval_decision,
        "summary": report["summary"],
        "global_abort_reasons": global_abort_reasons,
    }
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_path = reports_dir / f"ir36_destination_approval_gate_matrix_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "approval_report": report,
        "external_write_executed": False,
        "global_abort_reasons": global_abort_reasons,
    }


def write_ir36_completion_report(
    *,
    base_path: Path,
    ir36_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    adjacent_tests: dict[str, int] | None = None,
    scoped_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR36-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    adjacent = adjacent_tests or {"passed": 0, "failed": 0}
    scoped = scoped_regression or {"passed": 0, "failed": 0}

    approval = ir36_output.get("approval_report", {}) if isinstance(ir36_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 36",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR36_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "adjacent_ir34_ir36": adjacent,
            "scoped_regression": scoped,
        },
        "overall_approval_decision": approval.get("overall_approval_decision", "UNKNOWN"),
        "source_validation_result": approval.get("source_validation_result", "UNKNOWN"),
        "release_candidate_id": approval.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": approval.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(approval.get("validation_failed_checks", [])),
        "validation_warning_count": len(approval.get("validation_warnings", [])),
        "summary": approval.get("summary", {}),
        "artifacts": {
            "approval_report": ir36_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase36_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase36_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

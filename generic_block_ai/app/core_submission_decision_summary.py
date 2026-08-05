"""
core_submission_decision_summary.py - IR30

Create a final submission decision summary from IR29 submission dry-run report.
This phase does not permit external submission.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR29_SCHEMA_VERSION = "ir29_release_candidate_submission_dryrun_v1"
IR30_SCHEMA_VERSION = "ir30_submission_decision_summary_v1"

DECISION_READY_FOR_SUBMISSION_SUMMARY = "READY_FOR_SUBMISSION_SUMMARY"
DECISION_HOLD = "HOLD"
DECISION_NOT_ALLOWED = "NOT_ALLOWED"


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


def run_ir30_submission_decision_summary_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir29_submission_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR30-T1/T2/T3/T4
    Build submission decision summary from IR29 dry-run report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir29_path = ir29_submission_report_path or (reports_dir / "ir29_release_candidate_submission_dryrun_report_ir29_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []
    decision_reasons: list[str] = []

    release_candidate_id = "UNKNOWN"
    submission_allowed_conditions: list[dict[str, Any]] = []
    submission_not_allowed_conditions: list[dict[str, Any]] = []
    submission_hold_conditions: list[dict[str, Any]] = []

    if not ir29_path.exists():
        failed_checks.append(f"ir29 submission report not found: {ir29_path}")

    if not failed_checks:
        ir29 = _read_json(ir29_path)

        if ir29.get("schema_version") != IR29_SCHEMA_VERSION:
            failed_checks.append(f"ir29 schema_version must be {IR29_SCHEMA_VERSION}")

        release_candidate_id = str(ir29.get("release_candidate_id", "UNKNOWN"))
        validation_result = str(ir29.get("validation_result", "UNKNOWN"))

        summary = ir29.get("summary", {}) if isinstance(ir29.get("summary"), dict) else {}
        send_allowed = bool(summary.get("send_allowed", False))
        send_executed = bool(summary.get("send_executed", False))

        safeguards = ir29.get("safeguards", {}) if isinstance(ir29.get("safeguards"), dict) else {}
        network_transmission_executed = bool(safeguards.get("network_transmission_executed", True))
        execution_policy_execute = bool(safeguards.get("execution_policy_execute", True))

        submission_allowed_conditions = [
            {
                "id": "A1",
                "description": "IR29 validation_result is PASS",
                "status": validation_result == "PASS",
            },
            {
                "id": "A2",
                "description": "release_candidate_id is present",
                "status": bool(release_candidate_id and release_candidate_id != "UNKNOWN"),
            },
            {
                "id": "A3",
                "description": "send_allowed remains false in dry-run",
                "status": send_allowed is False,
            },
        ]

        submission_not_allowed_conditions = [
            {
                "id": "N1",
                "description": "send_executed must remain false",
                "status": send_executed is False,
            },
            {
                "id": "N2",
                "description": "network_transmission_executed must remain false",
                "status": network_transmission_executed is False,
            },
            {
                "id": "N3",
                "description": "execution_policy_execute must remain false",
                "status": execution_policy_execute is False,
            },
        ]

        submission_hold_conditions = [
            {
                "id": "H1",
                "description": "validation warnings must be reviewed if present",
                "status": len(ir29.get("validation_warnings", [])) == 0,
            },
            {
                "id": "H2",
                "description": "failed checks must be zero",
                "status": len(ir29.get("validation_failed_checks", [])) == 0,
            },
        ]

        all_allowed_ok = all(item["status"] for item in submission_allowed_conditions)
        all_not_allowed_ok = all(item["status"] for item in submission_not_allowed_conditions)
        all_hold_ok = all(item["status"] for item in submission_hold_conditions)

        if not all_not_allowed_ok:
            final_decision = DECISION_NOT_ALLOWED
            decision_reasons.append("non_send_guard_violation")
        elif all_allowed_ok and all_hold_ok:
            final_decision = DECISION_READY_FOR_SUBMISSION_SUMMARY
            decision_reasons.append("dryrun_submission_summary_ready")
        else:
            final_decision = DECISION_HOLD
            decision_reasons.append("requires_manual_hold_resolution")
            if not all_allowed_ok:
                warnings.append("one or more allowed conditions are not satisfied")
            if not all_hold_ok:
                warnings.append("one or more hold conditions require review")
    else:
        final_decision = DECISION_NOT_ALLOWED
        decision_reasons.append("ir29_prerequisite_missing")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    decision_table = {
        "schema_version": IR30_SCHEMA_VERSION,
        "phase": "IR30",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_decision,
        "decision_reasons": decision_reasons,
        "submission_allowed_conditions": submission_allowed_conditions,
        "submission_not_allowed_conditions": submission_not_allowed_conditions,
        "submission_hold_conditions": submission_hold_conditions,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }

    table_path = reports_dir / f"ir30_submission_decision_table_{_safe(source_task_id)}.json"
    table_path.write_text(json.dumps(decision_table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": IR30_SCHEMA_VERSION,
        "phase": "IR30",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "final_submission_decision": final_decision,
            "reason_count": len(decision_reasons),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "send_allowed_invariant_ok": all(
                item.get("status", False)
                for item in submission_not_allowed_conditions
                if item.get("id") in {"N1", "N2", "N3"}
            ) if submission_not_allowed_conditions else False,
        },
        "artifacts": {
            "ir29_submission_report": _to_ref(ir29_path, project_root) if ir29_path.exists() else str(ir29_path),
            "submission_decision_table": _to_ref(table_path, project_root),
            "completion_report": "reports/implementation_restart_phase30_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }

    out_path = reports_dir / f"ir30_submission_decision_summary_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "decision_report": report,
        "external_write_executed": False,
    }


def write_ir30_completion_report(
    *,
    base_path: Path,
    ir30_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR30-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    decision = ir30_output.get("decision_report", {}) if isinstance(ir30_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 30",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR30_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": decision.get("validation_result", "UNKNOWN"),
        "release_candidate_id": decision.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": decision.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(decision.get("validation_failed_checks", [])),
        "validation_warning_count": len(decision.get("validation_warnings", [])),
        "summary": decision.get("summary", {}),
        "artifacts": {
            "decision_report": ir30_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase30_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase30_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

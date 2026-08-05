"""
core_submission_audit_narrative_builder.py - IR31

Build submission audit narrative artifacts from IR30 submission decision summary.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR30_SCHEMA_VERSION = "ir30_submission_decision_summary_v1"
IR31_SCHEMA_VERSION = "ir31_submission_audit_narrative_v1"


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


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir31_submission_audit_narrative_builder_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir30_decision_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR31-T1/T2/T3/T4
    Build audit narrative artifacts from IR30 submission decision summary report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir30_path = ir30_decision_report_path or (reports_dir / "ir30_submission_decision_summary_report_ir30_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    decision_reasons: list[str] = []
    send_allowed_invariant_ok = False
    decision_table_ref = ""

    if not ir30_path.exists():
        failed_checks.append(f"ir30 decision report not found: {ir30_path}")
    else:
        ir30 = _read_json(ir30_path)

        if ir30.get("schema_version") != IR30_SCHEMA_VERSION:
            failed_checks.append(f"ir30 schema_version must be {IR30_SCHEMA_VERSION}")

        release_candidate_id = str(ir30.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir30.get("final_submission_decision", "UNKNOWN"))

        summary = ir30.get("summary", {}) if isinstance(ir30.get("summary"), dict) else {}
        send_allowed_invariant_ok = bool(summary.get("send_allowed_invariant_ok", False))

        artifacts = ir30.get("artifacts", {}) if isinstance(ir30.get("artifacts"), dict) else {}
        decision_table_ref = str(artifacts.get("submission_decision_table", ""))

        if not send_allowed_invariant_ok:
            warnings.append("send_allowed invariant is not satisfied")

        if final_submission_decision == "NOT_ALLOWED":
            warnings.append("final submission decision is NOT_ALLOWED")
        elif final_submission_decision == "HOLD":
            warnings.append("final submission decision is HOLD")

        if decision_table_ref:
            decision_table_path = _resolve(project_root, decision_table_ref)
            if not decision_table_path.exists():
                failed_checks.append(f"ir30 decision table not found: {decision_table_path}")
            else:
                table = _read_json(decision_table_path)
                if table.get("schema_version") == IR30_SCHEMA_VERSION:
                    decision_reasons = [str(x) for x in table.get("decision_reasons", [])]
                    if str(table.get("final_submission_decision", "")) != final_submission_decision:
                        failed_checks.append("final_submission_decision mismatch between ir30 report and decision table")
                else:
                    failed_checks.append(f"ir30 decision table schema_version must be {IR30_SCHEMA_VERSION}")
        else:
            failed_checks.append("ir30 report artifacts.submission_decision_table is missing")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    narrative_dir = reports_dir / f"ir31_submission_audit_narrative_{_safe(source_task_id)}"
    narrative_dir.mkdir(parents=True, exist_ok=True)

    narrative_md_path = narrative_dir / "submission_audit_narrative.md"
    audit_index_path = narrative_dir / "submission_audit_index.json"
    reviewer_summary_path = narrative_dir / "reviewer_summary.json"

    narrative_lines = [
        "# IR31 Submission Audit Narrative",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Final Submission Decision: {final_submission_decision}",
        f"- Validation Result: {validation_result}",
        f"- Send Allowed Invariant OK: {str(send_allowed_invariant_ok).lower()}",
        "",
        "## Decision Reasons",
    ]
    if decision_reasons:
        for reason in decision_reasons:
            narrative_lines.append(f"- {reason}")
    else:
        narrative_lines.append("- none")

    narrative_lines.extend([
        "",
        "## Safety Position",
        "- This phase generates audit narrative only.",
        "- External submission remains disabled.",
        "- Production release remains disabled.",
    ])
    _write_markdown(narrative_md_path, narrative_lines)

    audit_index = {
        "schema_version": IR31_SCHEMA_VERSION,
        "phase": "IR31",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "index": {
            "ir30_decision_report": _to_ref(ir30_path, project_root) if ir30_path.exists() else str(ir30_path),
            "ir30_decision_table": decision_table_ref,
            "narrative_markdown": _to_ref(narrative_md_path, project_root),
            "reviewer_summary": _to_ref(reviewer_summary_path, project_root),
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
    audit_index_path.write_text(json.dumps(audit_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    reviewer_summary = {
        "schema_version": IR31_SCHEMA_VERSION,
        "phase": "IR31",
        "generated_at": _now_iso(),
        "release_candidate_id": release_candidate_id,
        "summary_text": "Submission decision summary is prepared for audit review; execution remains dry-run only.",
        "final_submission_decision": final_submission_decision,
        "decision_reasons": decision_reasons,
        "send_allowed_invariant_ok": send_allowed_invariant_ok,
        "validation_result": validation_result,
    }
    reviewer_summary_path.write_text(json.dumps(reviewer_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": IR31_SCHEMA_VERSION,
        "phase": "IR31",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "reason_count": len(decision_reasons),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "send_allowed_invariant_ok": send_allowed_invariant_ok,
        },
        "artifacts": {
            "narrative_dir": _to_ref(narrative_dir, project_root),
            "submission_audit_narrative": _to_ref(narrative_md_path, project_root),
            "submission_audit_index": _to_ref(audit_index_path, project_root),
            "reviewer_summary": _to_ref(reviewer_summary_path, project_root),
            "completion_report": "reports/implementation_restart_phase31_completion_report.json",
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

    out_path = reports_dir / f"ir31_submission_audit_narrative_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "narrative_report": report,
        "external_write_executed": False,
    }


def write_ir31_completion_report(
    *,
    base_path: Path,
    ir31_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR31-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    narrative = ir31_output.get("narrative_report", {}) if isinstance(ir31_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 31",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR31_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": narrative.get("validation_result", "UNKNOWN"),
        "release_candidate_id": narrative.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": narrative.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(narrative.get("validation_failed_checks", [])),
        "validation_warning_count": len(narrative.get("validation_warnings", [])),
        "summary": narrative.get("summary", {}),
        "artifacts": {
            "narrative_report": ir31_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase31_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase31_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

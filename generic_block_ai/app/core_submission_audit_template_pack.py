"""
core_submission_audit_template_pack.py - IR32

Build a submission audit template pack from IR31 narrative artifacts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR31_SCHEMA_VERSION = "ir31_submission_audit_narrative_v1"
IR32_SCHEMA_VERSION = "ir32_submission_audit_template_pack_v1"


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


def run_ir32_submission_audit_template_pack_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir31_narrative_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR32-T1/T2/T3/T4
    Build fixed audit submission templates from IR31 narrative outputs.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir31_path = ir31_narrative_report_path or (reports_dir / "ir31_submission_audit_narrative_report_ir31_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"
    send_allowed_invariant_ok = False

    narrative_ref = ""
    audit_index_ref = ""
    reviewer_summary_ref = ""

    if not ir31_path.exists():
        failed_checks.append(f"ir31 narrative report not found: {ir31_path}")
    else:
        ir31 = _read_json(ir31_path)

        if ir31.get("schema_version") != IR31_SCHEMA_VERSION:
            failed_checks.append(f"ir31 schema_version must be {IR31_SCHEMA_VERSION}")

        if ir31.get("validation_result") != "PASS":
            failed_checks.append("ir31 validation_result must be PASS")

        release_candidate_id = str(ir31.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir31.get("final_submission_decision", "UNKNOWN"))

        summary = ir31.get("summary", {}) if isinstance(ir31.get("summary"), dict) else {}
        send_allowed_invariant_ok = bool(summary.get("send_allowed_invariant_ok", False))

        artifacts = ir31.get("artifacts", {}) if isinstance(ir31.get("artifacts"), dict) else {}
        narrative_ref = str(artifacts.get("submission_audit_narrative", ""))
        audit_index_ref = str(artifacts.get("submission_audit_index", ""))
        reviewer_summary_ref = str(artifacts.get("reviewer_summary", ""))

        for label, ref in [
            ("submission_audit_narrative", narrative_ref),
            ("submission_audit_index", audit_index_ref),
            ("reviewer_summary", reviewer_summary_ref),
        ]:
            if not ref:
                failed_checks.append(f"ir31 artifacts.{label} is missing")
                continue
            target = _resolve(project_root, ref)
            if not target.exists() or not target.is_file():
                failed_checks.append(f"ir31 artifact {label} not found: {target}")

        if not send_allowed_invariant_ok:
            warnings.append("send_allowed invariant is not satisfied")
        if final_submission_decision != "READY_FOR_SUBMISSION_SUMMARY":
            warnings.append("final_submission_decision is not READY_FOR_SUBMISSION_SUMMARY")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    pack_dir = reports_dir / f"ir32_submission_audit_template_pack_{_safe(source_task_id)}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    cover_path = pack_dir / "submission_cover.md"
    attachments_path = pack_dir / "attachment_list.json"
    signature_path = pack_dir / "confirmation_signature_sheet.md"
    reviewer_template_path = pack_dir / "review_template.md"

    cover_lines = [
        "# Submission Cover",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Final Submission Decision: {final_submission_decision}",
        f"- Template Pack Validation: {validation_result}",
        "- Submission Mode: dry_run_only",
        "",
        "## Scope",
        "- This package is for audit review preparation only.",
        "- External submission remains disabled.",
        "- Production release remains disabled.",
    ]
    _write_markdown(cover_path, cover_lines)

    attachments = {
        "schema_version": IR32_SCHEMA_VERSION,
        "phase": "IR32",
        "generated_at": _now_iso(),
        "release_candidate_id": release_candidate_id,
        "attachments": [
            {
                "name": "submission_audit_narrative",
                "path": narrative_ref,
                "required": True,
            },
            {
                "name": "submission_audit_index",
                "path": audit_index_ref,
                "required": True,
            },
            {
                "name": "reviewer_summary",
                "path": reviewer_summary_ref,
                "required": True,
            },
        ],
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }
    attachments_path.write_text(json.dumps(attachments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signature_lines = [
        "# Confirmation Signature Sheet",
        "",
        f"Release Candidate ID: {release_candidate_id}",
        "",
        "| Role | Name | Date | Signature |",
        "|---|---|---|---|",
        "| Reviewer |  |  |  |",
        "| Approver |  |  |  |",
        "| Audit Owner |  |  |  |",
        "",
        "Notes:",
        "- Signing this sheet does not trigger external submission.",
        "- External transmission remains prohibited in IR32.",
    ]
    _write_markdown(signature_path, signature_lines)

    reviewer_lines = [
        "# Review Template",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Final Submission Decision: {final_submission_decision}",
        f"- Send Allowed Invariant OK: {str(send_allowed_invariant_ok).lower()}",
        "",
        "## Review Checklist",
        "- Narrative content reviewed",
        "- Audit index consistency checked",
        "- Reviewer summary validated",
        "- send_allowed=false invariant reconfirmed",
        "- External submission NOT executed",
    ]
    _write_markdown(reviewer_template_path, reviewer_lines)

    report = {
        "schema_version": IR32_SCHEMA_VERSION,
        "phase": "IR32",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "template_file_count": 4,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "send_allowed_invariant_ok": send_allowed_invariant_ok,
        },
        "artifacts": {
            "template_pack_dir": _to_ref(pack_dir, project_root),
            "submission_cover": _to_ref(cover_path, project_root),
            "attachment_list": _to_ref(attachments_path, project_root),
            "confirmation_signature_sheet": _to_ref(signature_path, project_root),
            "review_template": _to_ref(reviewer_template_path, project_root),
            "completion_report": "reports/implementation_restart_phase32_completion_report.json",
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

    out_path = reports_dir / f"ir32_submission_audit_template_pack_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "template_report": report,
        "external_write_executed": False,
    }


def write_ir32_completion_report(
    *,
    base_path: Path,
    ir32_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR32-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    template = ir32_output.get("template_report", {}) if isinstance(ir32_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 32",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR32_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": template.get("validation_result", "UNKNOWN"),
        "release_candidate_id": template.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": template.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(template.get("validation_failed_checks", [])),
        "validation_warning_count": len(template.get("validation_warnings", [])),
        "summary": template.get("summary", {}),
        "artifacts": {
            "template_report": ir32_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase32_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase32_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

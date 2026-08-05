"""
core_submission_package_recomposition_rules.py - IR33

Define recomposition rules for submission packages from IR32 template pack.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR32_SCHEMA_VERSION = "ir32_submission_audit_template_pack_v1"
IR33_SCHEMA_VERSION = "ir33_submission_package_recomposition_rules_v1"


DESTINATION_RULES = {
    "regulatory_audit": {
        "required_templates": [
            "submission_cover",
            "attachment_list",
            "confirmation_signature_sheet",
        ],
        "optional_templates": [
            "review_template",
        ],
        "priority": 1,
    },
    "internal_review_board": {
        "required_templates": [
            "submission_cover",
            "review_template",
        ],
        "optional_templates": [
            "attachment_list",
            "confirmation_signature_sheet",
        ],
        "priority": 2,
    },
    "compliance_archive": {
        "required_templates": [
            "submission_cover",
            "attachment_list",
            "confirmation_signature_sheet",
            "review_template",
        ],
        "optional_templates": [],
        "priority": 3,
    },
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


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir33_submission_package_recomposition_rules_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir32_template_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR33-T1/T2/T3/T4
    Build destination-specific recomposition rules and resubmission templates.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir32_path = ir32_template_report_path or (reports_dir / "ir32_submission_audit_template_pack_report_ir32_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"

    template_refs: dict[str, str] = {
        "submission_cover": "",
        "attachment_list": "",
        "confirmation_signature_sheet": "",
        "review_template": "",
    }

    if not ir32_path.exists():
        failed_checks.append(f"ir32 template report not found: {ir32_path}")
    else:
        ir32 = _read_json(ir32_path)

        if ir32.get("schema_version") != IR32_SCHEMA_VERSION:
            failed_checks.append(f"ir32 schema_version must be {IR32_SCHEMA_VERSION}")
        if ir32.get("validation_result") != "PASS":
            failed_checks.append("ir32 validation_result must be PASS")

        release_candidate_id = str(ir32.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir32.get("final_submission_decision", "UNKNOWN"))

        summary = ir32.get("summary", {}) if isinstance(ir32.get("summary"), dict) else {}
        if not bool(summary.get("send_allowed_invariant_ok", False)):
            warnings.append("send_allowed invariant is not satisfied")

        artifacts = ir32.get("artifacts", {}) if isinstance(ir32.get("artifacts"), dict) else {}
        template_refs["submission_cover"] = str(artifacts.get("submission_cover", ""))
        template_refs["attachment_list"] = str(artifacts.get("attachment_list", ""))
        template_refs["confirmation_signature_sheet"] = str(artifacts.get("confirmation_signature_sheet", ""))
        template_refs["review_template"] = str(artifacts.get("review_template", ""))

        for key, ref in template_refs.items():
            if not ref:
                failed_checks.append(f"ir32 artifacts.{key} is missing")
                continue
            path = _resolve(project_root, ref)
            if not path.exists() or not path.is_file():
                failed_checks.append(f"template artifact not found ({key}): {path}")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    rules_dir = reports_dir / f"ir33_submission_package_recomposition_rules_{_safe(source_task_id)}"
    rules_dir.mkdir(parents=True, exist_ok=True)

    destination_rules_path = rules_dir / "destination_recomposition_rules.json"
    resubmission_rules_path = rules_dir / "resubmission_recomposition_rules.json"
    rollback_template_path = rules_dir / "rollback_response_template.md"
    recomposition_matrix_path = rules_dir / "recomposition_matrix.json"

    destination_rules = {
        "schema_version": IR33_SCHEMA_VERSION,
        "phase": "IR33",
        "generated_at": _now_iso(),
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "destinations": DESTINATION_RULES,
        "template_refs": template_refs,
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
            "network_transmission_executed": False,
        },
    }
    destination_rules_path.write_text(json.dumps(destination_rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    resubmission_rules = {
        "schema_version": IR33_SCHEMA_VERSION,
        "phase": "IR33",
        "generated_at": _now_iso(),
        "release_candidate_id": release_candidate_id,
        "rules": [
            {
                "id": "R1",
                "name": "preserve_release_candidate_id",
                "description": "Reuse release_candidate_id for dry-run resubmission summaries unless IR26 is reissued.",
            },
            {
                "id": "R2",
                "name": "rebuild_attachment_list",
                "description": "Always regenerate attachment_list when narrative/index/reviewer summary changes.",
            },
            {
                "id": "R3",
                "name": "refresh_signature_sheet",
                "description": "Signature sheet date/signature fields are blanked and reissued for each resubmission cycle.",
            },
            {
                "id": "R4",
                "name": "no_external_submission",
                "description": "External transmission remains prohibited in IR33 dry-run.",
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
    resubmission_rules_path.write_text(json.dumps(resubmission_rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rollback_lines = [
        "# Rollback Response Template",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        "- Purpose: Handle submission package return/rework without external transmission.",
        "",
        "## Return Reason",
        "- [ ] Missing template field",
        "- [ ] Attachment mismatch",
        "- [ ] Signature section incomplete",
        "- [ ] Reviewer clarification requested",
        "",
        "## Recomposition Actions",
        "1. Rebuild templates based on destination rules.",
        "2. Re-run IR30 decision summary and IR31 narrative if needed.",
        "3. Regenerate IR32 template pack and IR33 recomposition outputs.",
        "",
        "## Guard Confirmation",
        "- send_allowed remains false",
        "- send_executed remains false",
        "- network_transmission_executed remains false",
    ]
    _write_markdown(rollback_template_path, rollback_lines)

    matrix = {
        "schema_version": IR33_SCHEMA_VERSION,
        "phase": "IR33",
        "generated_at": _now_iso(),
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "matrix": [
            {
                "destination": destination,
                "required_count": len(rule["required_templates"]),
                "optional_count": len(rule["optional_templates"]),
                "priority": rule["priority"],
            }
            for destination, rule in DESTINATION_RULES.items()
        ],
    }
    recomposition_matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": IR33_SCHEMA_VERSION,
        "phase": "IR33",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_rule_count": len(DESTINATION_RULES),
            "template_file_count": 4,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
        },
        "artifacts": {
            "rules_dir": _to_ref(rules_dir, project_root),
            "destination_recomposition_rules": _to_ref(destination_rules_path, project_root),
            "resubmission_recomposition_rules": _to_ref(resubmission_rules_path, project_root),
            "rollback_response_template": _to_ref(rollback_template_path, project_root),
            "recomposition_matrix": _to_ref(recomposition_matrix_path, project_root),
            "completion_report": "reports/implementation_restart_phase33_completion_report.json",
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

    out_path = reports_dir / f"ir33_submission_package_recomposition_rules_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "recomposition_report": report,
        "external_write_executed": False,
    }


def write_ir33_completion_report(
    *,
    base_path: Path,
    ir33_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR33-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    recomposition = ir33_output.get("recomposition_report", {}) if isinstance(ir33_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 33",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR33_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": recomposition.get("validation_result", "UNKNOWN"),
        "release_candidate_id": recomposition.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": recomposition.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(recomposition.get("validation_failed_checks", [])),
        "validation_warning_count": len(recomposition.get("validation_warnings", [])),
        "summary": recomposition.get("summary", {}),
        "artifacts": {
            "recomposition_report": ir33_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase33_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase33_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

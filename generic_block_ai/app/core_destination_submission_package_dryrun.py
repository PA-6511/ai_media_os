"""
core_destination_submission_package_dryrun.py - IR34

Generate destination-specific submission packages in dry-run mode from IR33
recomposition rules and run resubmission recomposition simulation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR33_SCHEMA_VERSION = "ir33_submission_package_recomposition_rules_v1"
IR34_SCHEMA_VERSION = "ir34_destination_submission_package_dryrun_v1"


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


def run_ir34_destination_submission_package_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir33_recomposition_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR34-T1/T2/T3/T4
    Build destination submission package artifacts and resubmission simulation.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir33_path = ir33_recomposition_report_path or (
        reports_dir / "ir33_submission_package_recomposition_rules_report_ir33_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"

    destination_rules_path: Path | None = None
    resubmission_rules_path: Path | None = None
    rollback_template_path: Path | None = None

    destination_summaries: list[dict[str, Any]] = []

    if not ir33_path.exists():
        failed_checks.append(f"ir33 recomposition report not found: {ir33_path}")

    if not failed_checks:
        ir33 = _read_json(ir33_path)
        if ir33.get("schema_version") != IR33_SCHEMA_VERSION:
            failed_checks.append(f"ir33 schema_version must be {IR33_SCHEMA_VERSION}")
        if ir33.get("validation_result") != "PASS":
            failed_checks.append("ir33 validation_result must be PASS")

        release_candidate_id = str(ir33.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir33.get("final_submission_decision", "UNKNOWN"))

        artifacts = ir33.get("artifacts", {}) if isinstance(ir33.get("artifacts"), dict) else {}
        rules_ref = str(artifacts.get("destination_recomposition_rules", ""))
        resub_ref = str(artifacts.get("resubmission_recomposition_rules", ""))
        rollback_ref = str(artifacts.get("rollback_response_template", ""))

        if not rules_ref:
            failed_checks.append("ir33 artifacts.destination_recomposition_rules is missing")
        else:
            destination_rules_path = _resolve(project_root, rules_ref)
            if not destination_rules_path.exists():
                failed_checks.append(f"destination rules file not found: {destination_rules_path}")

        if not resub_ref:
            failed_checks.append("ir33 artifacts.resubmission_recomposition_rules is missing")
        else:
            resubmission_rules_path = _resolve(project_root, resub_ref)
            if not resubmission_rules_path.exists():
                failed_checks.append(f"resubmission rules file not found: {resubmission_rules_path}")

        if not rollback_ref:
            failed_checks.append("ir33 artifacts.rollback_response_template is missing")
        else:
            rollback_template_path = _resolve(project_root, rollback_ref)
            if not rollback_template_path.exists():
                failed_checks.append(f"rollback template not found: {rollback_template_path}")

    package_root = reports_dir / f"ir34_destination_submission_packages_{_safe(source_task_id)}"
    package_root.mkdir(parents=True, exist_ok=True)

    simulation_path = package_root / "resubmission_recomposition_simulation.json"

    if not failed_checks and destination_rules_path is not None:
        destination_rules = _read_json(destination_rules_path)
        template_refs = destination_rules.get("template_refs", {}) if isinstance(destination_rules.get("template_refs"), dict) else {}
        destinations = destination_rules.get("destinations", {}) if isinstance(destination_rules.get("destinations"), dict) else {}

        for destination_name, destination_rule in destinations.items():
            if not isinstance(destination_rule, dict):
                failed_checks.append(f"destination rule format invalid: {destination_name}")
                continue

            required_templates = destination_rule.get("required_templates", [])
            optional_templates = destination_rule.get("optional_templates", [])

            if not isinstance(required_templates, list) or not isinstance(optional_templates, list):
                failed_checks.append(f"destination template lists invalid: {destination_name}")
                continue

            required_resolved: list[dict[str, str]] = []
            optional_resolved: list[dict[str, str]] = []

            missing_required: list[str] = []
            missing_optional: list[str] = []

            for template_key in required_templates:
                ref = str(template_refs.get(str(template_key), ""))
                if not ref:
                    missing_required.append(str(template_key))
                    continue
                path = _resolve(project_root, ref)
                if not path.exists() or not path.is_file():
                    missing_required.append(str(template_key))
                    continue
                required_resolved.append({
                    "template": str(template_key),
                    "path": _to_ref(path, project_root),
                })

            for template_key in optional_templates:
                ref = str(template_refs.get(str(template_key), ""))
                if not ref:
                    missing_optional.append(str(template_key))
                    continue
                path = _resolve(project_root, ref)
                if not path.exists() or not path.is_file():
                    missing_optional.append(str(template_key))
                    continue
                optional_resolved.append({
                    "template": str(template_key),
                    "path": _to_ref(path, project_root),
                })

            if missing_required:
                failed_checks.append(
                    f"destination {destination_name} missing required templates: {sorted(missing_required)}"
                )
            if missing_optional:
                warnings.append(
                    f"destination {destination_name} missing optional templates: {sorted(missing_optional)}"
                )

            destination_dir = package_root / str(destination_name)
            destination_dir.mkdir(parents=True, exist_ok=True)

            manifest = {
                "schema_version": IR34_SCHEMA_VERSION,
                "phase": "IR34",
                "generated_at": _now_iso(),
                "source_task_id": source_task_id,
                "release_candidate_id": release_candidate_id,
                "destination": str(destination_name),
                "required_templates": required_resolved,
                "optional_templates": optional_resolved,
                "missing_required_templates": sorted(missing_required),
                "missing_optional_templates": sorted(missing_optional),
                "submission_mode": "dry_run_only",
                "send_guard": {
                    "send_allowed": False,
                    "send_executed": False,
                    "network_transmission_executed": False,
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

            manifest_path = destination_dir / "destination_package_manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            destination_summaries.append(
                {
                    "destination": str(destination_name),
                    "required_count": len(required_resolved),
                    "optional_count": len(optional_resolved),
                    "missing_required_count": len(missing_required),
                    "missing_optional_count": len(missing_optional),
                    "manifest_path": _to_ref(manifest_path, project_root),
                }
            )

    simulation = {
        "schema_version": IR34_SCHEMA_VERSION,
        "phase": "IR34",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "simulation": {
            "resubmission_rule_file": _to_ref(resubmission_rules_path, project_root) if resubmission_rules_path and resubmission_rules_path.exists() else "UNKNOWN",
            "rollback_template_file": _to_ref(rollback_template_path, project_root) if rollback_template_path and rollback_template_path.exists() else "UNKNOWN",
            "destination_package_count": len(destination_summaries),
            "recomposition_executed": True,
            "external_submission_executed": False,
            "network_transmission_executed": False,
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
    simulation_path.write_text(json.dumps(simulation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR34_SCHEMA_VERSION,
        "phase": "IR34",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_package_count": len(destination_summaries),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "resubmission_simulation_executed": True,
            "external_submission_executed": False,
        },
        "destination_packages": destination_summaries,
        "artifacts": {
            "package_root": _to_ref(package_root, project_root),
            "resubmission_simulation": _to_ref(simulation_path, project_root),
            "completion_report": "reports/implementation_restart_phase34_completion_report.json",
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

    out_path = reports_dir / f"ir34_destination_submission_package_dryrun_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "dryrun_report": report,
        "external_write_executed": False,
    }


def write_ir34_completion_report(
    *,
    base_path: Path,
    ir34_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR34-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    dryrun = ir34_output.get("dryrun_report", {}) if isinstance(ir34_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 34",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR34_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": dryrun.get("validation_result", "UNKNOWN"),
        "release_candidate_id": dryrun.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": dryrun.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(dryrun.get("validation_failed_checks", [])),
        "validation_warning_count": len(dryrun.get("validation_warnings", [])),
        "summary": dryrun.get("summary", {}),
        "artifacts": {
            "dryrun_report": ir34_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase34_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase34_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
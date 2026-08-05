"""
core_destination_package_validation_matrix.py - IR35

Validate IR34 destination submission packages with destination-specific matrix
checks in dry-run mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR33_SCHEMA_VERSION = "ir33_submission_package_recomposition_rules_v1"
IR34_SCHEMA_VERSION = "ir34_destination_submission_package_dryrun_v1"
IR35_SCHEMA_VERSION = "ir35_destination_package_validation_matrix_v1"

RESUBMISSION_REQUIRED_RULE_IDS = {"R1", "R2", "R3", "R4"}


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


def _find_template_path(template_entries: list[dict[str, Any]], template_name: str, project_root: Path) -> Path | None:
    for entry in template_entries:
        if str(entry.get("template", "")) != template_name:
            continue
        ref = str(entry.get("path", ""))
        if not ref:
            return None
        return _resolve(project_root, ref)
    return None


def run_ir35_destination_package_validation_matrix_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir34_dryrun_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR35-T1/T2/T3/T4
    Build destination validation matrix over IR34 dry-run packages.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir34_path = ir34_dryrun_report_path or (
        reports_dir / "ir34_destination_submission_package_dryrun_report_ir34_live_trial.json"
    )

    failed_checks: list[str] = []
    warnings: list[str] = []
    destination_results: list[dict[str, Any]] = []

    release_candidate_id = "UNKNOWN"
    final_submission_decision = "UNKNOWN"

    package_root: Path | None = None
    simulation_path: Path | None = None
    destination_rules_path: Path | None = None
    resubmission_rules_path: Path | None = None

    if not ir34_path.exists():
        failed_checks.append(f"ir34 dryrun report not found: {ir34_path}")

    if not failed_checks:
        ir34 = _read_json(ir34_path)
        if ir34.get("schema_version") != IR34_SCHEMA_VERSION:
            failed_checks.append(f"ir34 schema_version must be {IR34_SCHEMA_VERSION}")
        if ir34.get("validation_result") != "PASS":
            failed_checks.append("ir34 validation_result must be PASS")

        release_candidate_id = str(ir34.get("release_candidate_id", "UNKNOWN"))
        final_submission_decision = str(ir34.get("final_submission_decision", "UNKNOWN"))

        artifacts = ir34.get("artifacts", {}) if isinstance(ir34.get("artifacts"), dict) else {}
        package_ref = str(artifacts.get("package_root", ""))
        simulation_ref = str(artifacts.get("resubmission_simulation", ""))

        if not package_ref:
            failed_checks.append("ir34 artifacts.package_root is missing")
        else:
            package_root = _resolve(project_root, package_ref)
            if not package_root.exists() or not package_root.is_dir():
                failed_checks.append(f"ir34 package_root not found: {package_root}")

        if not simulation_ref:
            failed_checks.append("ir34 artifacts.resubmission_simulation is missing")
        else:
            simulation_path = _resolve(project_root, simulation_ref)
            if not simulation_path.exists() or not simulation_path.is_file():
                failed_checks.append(f"ir34 resubmission simulation not found: {simulation_path}")

    simulation: dict[str, Any] = {}
    destination_rules: dict[str, Any] = {}
    resubmission_rules: dict[str, Any] = {}
    global_matrix_checks: dict[str, bool] = {
        "recomposition_executed": False,
        "external_submission_blocked": False,
        "network_transmission_blocked": False,
        "resubmission_rules_loaded": False,
        "required_resubmission_patterns_present": False,
    }

    if not failed_checks and simulation_path is not None:
        simulation = _read_json(simulation_path)
        simulation_payload = simulation.get("simulation", {}) if isinstance(simulation.get("simulation"), dict) else {}

        global_matrix_checks["recomposition_executed"] = bool(simulation_payload.get("recomposition_executed", False))
        global_matrix_checks["external_submission_blocked"] = not bool(simulation_payload.get("external_submission_executed", True))
        global_matrix_checks["network_transmission_blocked"] = not bool(simulation_payload.get("network_transmission_executed", True))

        if not global_matrix_checks["recomposition_executed"]:
            failed_checks.append("resubmission recomposition_executed must be true")
        if not global_matrix_checks["external_submission_blocked"]:
            failed_checks.append("external submission must remain blocked")
        if not global_matrix_checks["network_transmission_blocked"]:
            failed_checks.append("network transmission must remain blocked")

        rules_ref = str(simulation_payload.get("resubmission_rule_file", ""))
        if not rules_ref:
            failed_checks.append("resubmission_rule_file is missing in simulation")
        else:
            resubmission_rules_path = _resolve(project_root, rules_ref)
            if not resubmission_rules_path.exists() or not resubmission_rules_path.is_file():
                failed_checks.append(f"resubmission rule file not found: {resubmission_rules_path}")

    if not failed_checks and resubmission_rules_path is not None:
        resubmission_rules = _read_json(resubmission_rules_path)
        global_matrix_checks["resubmission_rules_loaded"] = True
        if resubmission_rules.get("schema_version") != IR33_SCHEMA_VERSION:
            failed_checks.append(f"resubmission rules schema_version must be {IR33_SCHEMA_VERSION}")

        rule_entries = resubmission_rules.get("rules", [])
        if not isinstance(rule_entries, list):
            failed_checks.append("resubmission rules list format is invalid")
            rule_ids: set[str] = set()
        else:
            rule_ids = {str(item.get("id", "")) for item in rule_entries if isinstance(item, dict)}

        global_matrix_checks["required_resubmission_patterns_present"] = RESUBMISSION_REQUIRED_RULE_IDS.issubset(rule_ids)
        if not global_matrix_checks["required_resubmission_patterns_present"]:
            missing = sorted(RESUBMISSION_REQUIRED_RULE_IDS - rule_ids)
            failed_checks.append(f"required resubmission rule ids are missing: {missing}")

    if not failed_checks and package_root is not None:
        # Destination rules are colocated with resubmission rules in IR33 outputs.
        if resubmission_rules_path is None:
            failed_checks.append("cannot resolve IR33 destination rules without resubmission rules path")
        else:
            destination_rules_path = resubmission_rules_path.parent / "destination_recomposition_rules.json"
            if not destination_rules_path.exists() or not destination_rules_path.is_file():
                failed_checks.append(f"destination recomposition rules not found: {destination_rules_path}")

    if not failed_checks and destination_rules_path is not None and package_root is not None:
        destination_rules = _read_json(destination_rules_path)
        if destination_rules.get("schema_version") != IR33_SCHEMA_VERSION:
            failed_checks.append(f"destination rules schema_version must be {IR33_SCHEMA_VERSION}")

        destinations = destination_rules.get("destinations", {}) if isinstance(destination_rules.get("destinations"), dict) else {}
        expected_template_refs = (
            destination_rules.get("template_refs", {}) if isinstance(destination_rules.get("template_refs"), dict) else {}
        )

        for destination_name, destination_rule in destinations.items():
            destination_failed: list[str] = []
            destination_warn: list[str] = []

            destination_dir = package_root / str(destination_name)
            manifest_path = destination_dir / "destination_package_manifest.json"

            required_templates_expected = []
            optional_templates_expected = []
            if isinstance(destination_rule, dict):
                required_templates_expected = [str(v) for v in destination_rule.get("required_templates", [])]
                optional_templates_expected = [str(v) for v in destination_rule.get("optional_templates", [])]
            else:
                destination_failed.append("destination rule format is invalid")

            if not manifest_path.exists() or not manifest_path.is_file():
                destination_failed.append("destination package manifest is missing")
                destination_results.append(
                    {
                        "destination": str(destination_name),
                        "manifest_path": _to_ref(manifest_path, project_root),
                        "validation_result": "FAIL",
                        "failed_checks": destination_failed,
                        "warnings": destination_warn,
                    }
                )
                continue

            manifest = _read_json(manifest_path)
            required_entries = (
                manifest.get("required_templates", []) if isinstance(manifest.get("required_templates"), list) else []
            )
            optional_entries = (
                manifest.get("optional_templates", []) if isinstance(manifest.get("optional_templates"), list) else []
            )

            required_templates_actual = [str(item.get("template", "")) for item in required_entries if isinstance(item, dict)]
            optional_templates_actual = [str(item.get("template", "")) for item in optional_entries if isinstance(item, dict)]

            required_missing = sorted(set(required_templates_expected) - set(required_templates_actual))
            optional_missing = sorted(set(optional_templates_expected) - set(optional_templates_actual))
            required_unexpected = sorted(set(required_templates_actual) - set(required_templates_expected))
            optional_unexpected = sorted(set(optional_templates_actual) - set(optional_templates_expected))

            if required_missing:
                destination_failed.append(f"missing required templates: {required_missing}")
            if required_unexpected:
                destination_failed.append(f"unexpected required templates: {required_unexpected}")

            if optional_unexpected:
                destination_failed.append(f"unexpected optional templates: {optional_unexpected}")
            if optional_missing:
                destination_warn.append(f"missing optional templates: {optional_missing}")

            # Forbidden template check: manifest must not include templates outside rule allowlist.
            allowed_templates = set(required_templates_expected) | set(optional_templates_expected)
            manifest_templates = set(required_templates_actual) | set(optional_templates_actual)
            forbidden_templates = sorted(manifest_templates - allowed_templates)
            if forbidden_templates:
                destination_failed.append(f"forbidden templates detected: {forbidden_templates}")

            # Signature sheet check: template file must include signature keyword.
            signature_template = "confirmation_signature_sheet"
            signature_required_or_optional = signature_template in manifest_templates
            signature_content_ok = False
            if signature_required_or_optional:
                signature_path = _find_template_path(required_entries + optional_entries, signature_template, project_root)
                if signature_path is None or not signature_path.exists() or not signature_path.is_file():
                    destination_failed.append("signature sheet path is missing")
                else:
                    signature_text = signature_path.read_text(encoding="utf-8")
                    signature_content_ok = "signature" in signature_text.lower()
                    if not signature_content_ok:
                        destination_failed.append("signature sheet content does not include signature field")

            # Attachment list consistency check.
            attachment_template = "attachment_list"
            attachment_present = attachment_template in manifest_templates
            attachment_json_valid = False
            attachment_entries_count = 0
            if attachment_present:
                attachment_path = _find_template_path(required_entries + optional_entries, attachment_template, project_root)
                if attachment_path is None or not attachment_path.exists() or not attachment_path.is_file():
                    destination_failed.append("attachment_list path is missing")
                else:
                    try:
                        attachment_payload = _read_json(attachment_path)
                        attachments = attachment_payload.get("attachments", []) if isinstance(attachment_payload, dict) else []
                        attachment_json_valid = isinstance(attachments, list)
                        if not attachment_json_valid:
                            destination_failed.append("attachment_list.attachments must be a list")
                        else:
                            attachment_entries_count = len(attachments)
                    except json.JSONDecodeError:
                        destination_failed.append("attachment_list is not valid json")

            # Destination directory must only hold package manifest.
            if destination_dir.exists() and destination_dir.is_dir():
                extra_files = [
                    child.name
                    for child in destination_dir.iterdir()
                    if child.is_file() and child.name != "destination_package_manifest.json"
                ]
                if extra_files:
                    destination_failed.append(f"forbidden files in destination package dir: {sorted(extra_files)}")

            destination_validation_result = "FAIL" if destination_failed else ("WARN" if destination_warn else "PASS")
            destination_results.append(
                {
                    "destination": str(destination_name),
                    "manifest_path": _to_ref(manifest_path, project_root),
                    "validation_result": destination_validation_result,
                    "matrix_checks": {
                        "required_templates_complete": not required_missing and not required_unexpected,
                        "optional_templates_consistent": not optional_unexpected,
                        "forbidden_templates_absent": not forbidden_templates,
                        "signature_fields_valid": (not signature_required_or_optional) or signature_content_ok,
                        "attachment_integrity_valid": (not attachment_present) or attachment_json_valid,
                        "resubmission_patterns_valid": global_matrix_checks["required_resubmission_patterns_present"],
                    },
                    "counts": {
                        "required_expected": len(required_templates_expected),
                        "required_actual": len(required_templates_actual),
                        "optional_expected": len(optional_templates_expected),
                        "optional_actual": len(optional_templates_actual),
                        "attachment_entries": attachment_entries_count,
                    },
                    "failed_checks": destination_failed,
                    "warnings": destination_warn,
                }
            )

        # Ensure no unknown destination directory exists.
        known_destinations = {str(name) for name in destinations.keys()}
        unknown_destination_dirs = sorted(
            child.name
            for child in package_root.iterdir()
            if child.is_dir() and child.name not in known_destinations
        )
        if unknown_destination_dirs:
            failed_checks.append(f"unknown destination package directories detected: {unknown_destination_dirs}")

    for result in destination_results:
        for item in result.get("failed_checks", []):
            failed_checks.append(f"{result.get('destination')}: {item}")
        for item in result.get("warnings", []):
            warnings.append(f"{result.get('destination')}: {item}")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    matrix_root = reports_dir / f"ir35_destination_package_validation_matrix_{_safe(source_task_id)}"
    matrix_root.mkdir(parents=True, exist_ok=True)

    matrix_json_path = matrix_root / "destination_validation_matrix.json"
    matrix_md_path = matrix_root / "destination_validation_summary.md"

    matrix_payload = {
        "schema_version": IR35_SCHEMA_VERSION,
        "phase": "IR35",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "global_matrix_checks": global_matrix_checks,
        "destination_results": destination_results,
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
    matrix_json_path.write_text(json.dumps(matrix_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Destination Package Validation Matrix",
        "",
        f"- Source Task ID: {source_task_id}",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Validation Result: {validation_result}",
        "",
        "## Destination Results",
    ]
    for result in destination_results:
        md_lines.append(f"- {result['destination']}: {result['validation_result']}")
    md_lines.append("")
    md_lines.append("## Global Matrix Checks")
    for key, value in global_matrix_checks.items():
        md_lines.append(f"- {key}: {value}")
    matrix_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    report = {
        "schema_version": IR35_SCHEMA_VERSION,
        "phase": "IR35",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "final_submission_decision": final_submission_decision,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "destination_count": len(destination_results),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "required_resubmission_patterns_present": global_matrix_checks[
                "required_resubmission_patterns_present"
            ],
            "external_submission_executed": False,
        },
        "matrix": {
            "global_checks": global_matrix_checks,
            "destinations": destination_results,
        },
        "artifacts": {
            "matrix_root": _to_ref(matrix_root, project_root),
            "destination_validation_matrix": _to_ref(matrix_json_path, project_root),
            "destination_validation_summary": _to_ref(matrix_md_path, project_root),
            "completion_report": "reports/implementation_restart_phase35_completion_report.json",
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

    out_path = reports_dir / f"ir35_destination_package_validation_matrix_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "validation_report": report,
        "external_write_executed": False,
    }


def write_ir35_completion_report(
    *,
    base_path: Path,
    ir35_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR35-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    validation = ir35_output.get("validation_report", {}) if isinstance(ir35_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 35",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR35_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": validation.get("validation_result", "UNKNOWN"),
        "release_candidate_id": validation.get("release_candidate_id", "UNKNOWN"),
        "final_submission_decision": validation.get("final_submission_decision", "UNKNOWN"),
        "validation_failed_check_count": len(validation.get("validation_failed_checks", [])),
        "validation_warning_count": len(validation.get("validation_warnings", [])),
        "summary": validation.get("summary", {}),
        "artifacts": {
            "validation_report": ir35_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase35_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase35_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }
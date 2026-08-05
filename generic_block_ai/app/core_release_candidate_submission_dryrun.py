"""
core_release_candidate_submission_dryrun.py - IR29

Build a submission package from IR28 trace bundle in dry-run mode.
No external transmission is allowed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR28_SCHEMA_VERSION = "ir28_release_candidate_trace_bundle_v1"
IR29_SCHEMA_VERSION = "ir29_release_candidate_submission_dryrun_v1"


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


def _write_readme(path: Path, release_candidate_id: str, validation_result: str) -> None:
    lines = [
        "# IR29 Release Candidate Submission Dry-run",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Validation Result: {validation_result}",
        "- Submission mode: dry_run_only",
        "- External transmission attempted: false",
        "- Production release: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir29_release_candidate_submission_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir28_trace_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR29-T1/T2/T3/T4
    Build submission dry-run package from IR28 trace bundle.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir28_path = ir28_trace_report_path or (reports_dir / "ir28_release_candidate_trace_bundle_report_ir28_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    release_candidate_id = "UNKNOWN"
    included_artifact_count = 0

    precheck = {
        "schema_version": IR29_SCHEMA_VERSION,
        "phase": "IR29",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "checks": {
            "ir28_report_exists": False,
            "ir28_validation_pass": False,
            "trace_manifest_exists": False,
            "trace_sha256_manifest_exists": False,
            "release_candidate_id_present": False,
            "submission_mode_dry_run_only": True,
            "external_transmission_attempted": False,
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

    if not ir28_path.exists():
        failed_checks.append(f"ir28 trace report not found: {ir28_path}")
    else:
        precheck["checks"]["ir28_report_exists"] = True
        ir28 = _read_json(ir28_path)

        if ir28.get("schema_version") != IR28_SCHEMA_VERSION:
            failed_checks.append(f"ir28 schema_version must be {IR28_SCHEMA_VERSION}")
        if ir28.get("validation_result") != "PASS":
            failed_checks.append("ir28 validation_result must be PASS")
        else:
            precheck["checks"]["ir28_validation_pass"] = True

        release_candidate_id = str(ir28.get("release_candidate_id", "UNKNOWN"))
        if release_candidate_id != "UNKNOWN" and release_candidate_id:
            precheck["checks"]["release_candidate_id_present"] = True

        artifacts = ir28.get("artifacts", {}) if isinstance(ir28.get("artifacts"), dict) else {}
        trace_manifest_ref = str(artifacts.get("trace_manifest", ""))
        trace_sha_ref = str(artifacts.get("trace_sha256_manifest", ""))
        readme_ref = str(artifacts.get("readme", ""))

        trace_manifest_path = _resolve(project_root, trace_manifest_ref) if trace_manifest_ref else None
        trace_sha_path = _resolve(project_root, trace_sha_ref) if trace_sha_ref else None
        trace_readme_path = _resolve(project_root, readme_ref) if readme_ref else None

        if trace_manifest_path is None or not trace_manifest_path.exists():
            failed_checks.append(f"trace manifest not found: {trace_manifest_path}")
        else:
            precheck["checks"]["trace_manifest_exists"] = True

        if trace_sha_path is None or not trace_sha_path.exists():
            failed_checks.append(f"trace sha256 manifest not found: {trace_sha_path}")
        else:
            precheck["checks"]["trace_sha256_manifest_exists"] = True

        if trace_manifest_path is not None and trace_manifest_path.exists():
            trace_manifest = _read_json(trace_manifest_path)
            included_artifact_count = int(trace_manifest.get("counts", {}).get("included", 0)) if isinstance(trace_manifest.get("counts"), dict) else 0
            if str(trace_manifest.get("release_candidate_id", "")) != release_candidate_id:
                failed_checks.append("release_candidate_id mismatch between ir28 report and trace manifest")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    package_dir = reports_dir / f"ir29_release_candidate_submission_package_{_safe(source_task_id)}"
    package_dir.mkdir(parents=True, exist_ok=True)

    checklist_path = package_dir / "pre_submission_checklist.json"
    manifest_path = package_dir / "submission_package_manifest.json"
    readme_path = package_dir / "README.md"

    checklist_path.write_text(json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    package_manifest = {
        "schema_version": IR29_SCHEMA_VERSION,
        "phase": "IR29",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "validation_result": validation_result,
        "submission_mode": "dry_run_only",
        "send_guard": {
            "send_allowed": False,
            "send_executed": False,
            "network_transmission_executed": False,
            "reason": "ir29_submission_dryrun_only",
        },
        "prohibited_actions": [
            "external_network_submission",
            "production_release",
            "git_push",
        ],
        "summary": {
            "included_artifact_count": included_artifact_count,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
        },
        "artifacts": {
            "pre_submission_checklist": _to_ref(checklist_path, project_root),
            "source_ir28_report": _to_ref(ir28_path, project_root) if ir28_path.exists() else str(ir28_path),
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

    manifest_path.write_text(json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readme(readme_path, release_candidate_id, validation_result)

    report = {
        "schema_version": IR29_SCHEMA_VERSION,
        "phase": "IR29",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "validation_result": validation_result,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "included_artifact_count": included_artifact_count,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "send_allowed": False,
            "send_executed": False,
        },
        "artifacts": {
            "submission_package_dir": _to_ref(package_dir, project_root),
            "pre_submission_checklist": _to_ref(checklist_path, project_root),
            "submission_package_manifest": _to_ref(manifest_path, project_root),
            "readme": _to_ref(readme_path, project_root),
            "completion_report": "reports/implementation_restart_phase29_completion_report.json",
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

    out_path = reports_dir / f"ir29_release_candidate_submission_dryrun_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "submission_report": report,
        "external_write_executed": False,
    }


def write_ir29_completion_report(
    *,
    base_path: Path,
    ir29_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR29-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    submission = ir29_output.get("submission_report", {}) if isinstance(ir29_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 29",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR29_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": submission.get("validation_result", "UNKNOWN"),
        "release_candidate_id": submission.get("release_candidate_id", "UNKNOWN"),
        "validation_failed_check_count": len(submission.get("validation_failed_checks", [])),
        "validation_warning_count": len(submission.get("validation_warnings", [])),
        "summary": submission.get("summary", {}),
        "artifacts": {
            "submission_report": ir29_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase29_completion_report.json",
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

    out_path = reports_dir / "implementation_restart_phase29_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

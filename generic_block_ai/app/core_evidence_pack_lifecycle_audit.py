"""
core_evidence_pack_lifecycle_audit.py - IR23

Audit end-to-end lifecycle traceability across:
- IR20 evidence bundle generation
- IR21 evidence pack verification
- IR22 submission profile extraction
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR20_SCHEMA_VERSION = "ir20_cross_phase_evidence_bundle_v1"
IR21_SCHEMA_VERSION = "ir21_evidence_pack_verifier_v1"
IR22_SCHEMA_VERSION = "ir22_submission_profile_v1"
IR23_SCHEMA_VERSION = "ir23_evidence_pack_lifecycle_audit_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _path_matches(actual_value: str, expected_abs: Path, project_root: Path) -> bool:
    expected_rel = expected_abs.relative_to(project_root).as_posix()
    expected_abs_str = str(expected_abs.resolve())
    return actual_value in {expected_rel, expected_abs_str}


def run_ir23_evidence_pack_lifecycle_audit_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir20_bundle_report_path: Path | None = None,
    ir21_verifier_report_path: Path | None = None,
    ir22_completion_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR23-T1/T2/T3/T4
    Verify lifecycle traceability from IR20 bundle to IR22 submission profiles.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    bundle_report_path = ir20_bundle_report_path or (reports_dir / "ir20_cross_phase_evidence_bundle_ir20_live_trial.json")
    verifier_report_path = ir21_verifier_report_path or (reports_dir / "ir21_evidence_pack_verifier_report_ir21_live_trial.json")
    completion_report_path = ir22_completion_report_path or (reports_dir / "implementation_restart_phase22_completion_report.json")

    failures: list[str] = []
    warnings: list[str] = []

    for label, path in [
        ("ir20 bundle report", bundle_report_path),
        ("ir21 verifier report", verifier_report_path),
        ("ir22 completion report", completion_report_path),
    ]:
        if not path.exists():
            failures.append(f"{label} not found: {path}")

    profile_traceability: list[dict[str, Any]] = []
    profile_result_counts: dict[str, int] = {}
    ir22_profile_reports: list[str] = []

    if not failures:
        ir20_bundle = _read_json(bundle_report_path)
        ir21_verifier = _read_json(verifier_report_path)
        ir22_completion = _read_json(completion_report_path)

        if ir20_bundle.get("schema_version") != IR20_SCHEMA_VERSION:
            failures.append(f"ir20 bundle schema_version must be {IR20_SCHEMA_VERSION}")
        if ir21_verifier.get("schema_version") != IR21_SCHEMA_VERSION:
            failures.append(f"ir21 verifier schema_version must be {IR21_SCHEMA_VERSION}")
        if ir22_completion.get("schema_version") != IR22_SCHEMA_VERSION:
            failures.append(f"ir22 completion schema_version must be {IR22_SCHEMA_VERSION}")

        if ir20_bundle.get("validation_result") != "PASS":
            failures.append("ir20 bundle validation_result must be PASS")
        if ir21_verifier.get("validation_result") != "PASS":
            failures.append("ir21 verifier validation_result must be PASS")
        if ir22_completion.get("validation_result") == "FAIL":
            failures.append("ir22 completion validation_result must not be FAIL")

        ir21_artifacts = ir21_verifier.get("artifacts", {}) if isinstance(ir21_verifier.get("artifacts"), dict) else {}
        if not _path_matches(str(ir21_artifacts.get("bundle_report", "")), bundle_report_path, project_root):
            failures.append("ir21 verifier artifacts.bundle_report does not reference ir20 bundle report")

        ir20_manifest_rel = str(ir20_bundle.get("manifest_path", ""))
        ir20_sha_rel = str(ir20_bundle.get("sha256_manifest_path", ""))
        ir20_manifest_path = project_root / ir20_manifest_rel
        ir20_sha_path = project_root / ir20_sha_rel

        if not ir20_manifest_path.exists():
            failures.append(f"ir20 manifest not found: {ir20_manifest_path}")
        if not ir20_sha_path.exists():
            failures.append(f"ir20 sha256 manifest not found: {ir20_sha_path}")

        if not failures:
            ir20_manifest = _read_json(ir20_manifest_path)
            ir20_sha = _read_json(ir20_sha_path)
            ir20_included = ir20_manifest.get("included_artifacts", []) if isinstance(ir20_manifest.get("included_artifacts"), list) else []
            ir20_included_set = set(ir20_included)

            ir22_artifacts = ir22_completion.get("artifacts", {}) if isinstance(ir22_completion.get("artifacts"), dict) else {}
            ir22_profile_reports = [
                str(p) for p in ir22_artifacts.get("profile_reports", [])
                if isinstance(ir22_artifacts.get("profile_reports"), list)
            ]

            if not ir22_profile_reports:
                failures.append("ir22 completion has no profile_reports")

            for profile_report_rel in ir22_profile_reports:
                profile_report_path = project_root / profile_report_rel
                if not profile_report_path.exists():
                    failures.append(f"ir22 profile report not found: {profile_report_path}")
                    continue

                profile_report = _read_json(profile_report_path)
                if profile_report.get("schema_version") != IR22_SCHEMA_VERSION:
                    failures.append(f"ir22 profile report schema mismatch: {profile_report_rel}")
                    continue

                profile_name = str(profile_report.get("profile_name", "unknown"))
                profile_result = str(profile_report.get("validation_result", "UNKNOWN"))
                profile_result_counts[profile_result] = profile_result_counts.get(profile_result, 0) + 1

                profile_manifest_rel = str(profile_report.get("profile_manifest_path", ""))
                selected_sha_rel = str(profile_report.get("selected_sha256_manifest_path", ""))
                profile_manifest_path = project_root / profile_manifest_rel
                selected_sha_path = project_root / selected_sha_rel

                if not profile_manifest_path.exists():
                    failures.append(f"profile manifest not found: {profile_manifest_path}")
                    continue
                if not selected_sha_path.exists():
                    failures.append(f"profile selected sha manifest not found: {selected_sha_path}")
                    continue

                profile_manifest = _read_json(profile_manifest_path)
                selected_sha = _read_json(selected_sha_path)

                selected_artifacts = (
                    profile_manifest.get("selected_artifacts", [])
                    if isinstance(profile_manifest.get("selected_artifacts"), list)
                    else []
                )

                missing_in_ir20: list[str] = []
                sha_mismatch: list[str] = []

                for rel in selected_artifacts:
                    if rel not in ir20_included_set:
                        missing_in_ir20.append(rel)
                        continue
                    expected_sha = str(ir20_sha.get(rel, "")) if isinstance(ir20_sha, dict) else ""
                    actual_sha = str(selected_sha.get(rel, "")) if isinstance(selected_sha, dict) else ""
                    if not expected_sha or not actual_sha or expected_sha != actual_sha:
                        sha_mismatch.append(rel)

                if missing_in_ir20:
                    failures.append(f"profile selected artifacts missing in ir20 bundle ({profile_name}): {missing_in_ir20}")
                if sha_mismatch:
                    failures.append(f"profile sha mismatch vs ir20 ({profile_name}): {sha_mismatch}")

                profile_traceability.append(
                    {
                        "profile_name": profile_name,
                        "profile_source_task_id": str(profile_report.get("source_task_id", "unknown")),
                        "profile_report": profile_report_rel,
                        "selected_artifact_count": len(selected_artifacts),
                        "missing_in_ir20_count": len(missing_in_ir20),
                        "sha_mismatch_count": len(sha_mismatch),
                        "validation_result": profile_result,
                    }
                )

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR23_SCHEMA_VERSION,
        "phase": "IR23",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "profiles_checked": len(profile_traceability),
            "profile_result_counts": profile_result_counts,
            "failed_check_count": len(failures),
            "warning_count": len(warnings),
        },
        "traceability": {
            "ir20_bundle_report": str(bundle_report_path.relative_to(project_root).as_posix()) if bundle_report_path.exists() else str(bundle_report_path),
            "ir21_verifier_report": str(verifier_report_path.relative_to(project_root).as_posix()) if verifier_report_path.exists() else str(verifier_report_path),
            "ir22_completion_report": str(completion_report_path.relative_to(project_root).as_posix()) if completion_report_path.exists() else str(completion_report_path),
            "ir22_profile_reports": ir22_profile_reports,
            "profiles": profile_traceability,
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir23_evidence_pack_lifecycle_audit_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "lifecycle_report": report,
        "external_write_executed": False,
    }


def write_ir23_completion_report(
    *,
    base_path: Path,
    ir23_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR23-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    lifecycle = ir23_output.get("lifecycle_report", {}) if isinstance(ir23_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 23",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR23_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": lifecycle.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(lifecycle.get("validation_failed_checks", [])),
        "validation_warning_count": len(lifecycle.get("validation_warnings", [])),
        "summary": lifecycle.get("summary", {}),
        "artifacts": {
            "lifecycle_report": ir23_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase23_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase23_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

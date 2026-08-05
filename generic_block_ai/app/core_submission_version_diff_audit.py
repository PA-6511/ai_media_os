"""
core_submission_version_diff_audit.py - IR24

Audit version-to-version submission diffs using IR23 lifecycle reports.
This module verifies traceability and captures artifact/profile/sha256 deltas
for resubmission governance.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR20_SCHEMA_VERSION = "ir20_cross_phase_evidence_bundle_v1"
IR22_SCHEMA_VERSION = "ir22_submission_profile_v1"
IR23_SCHEMA_VERSION = "ir23_evidence_pack_lifecycle_audit_v1"
IR24_SCHEMA_VERSION = "ir24_submission_version_diff_audit_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _project_root_from_report(report_path: Path) -> Path:
    # Expected report path: <project_root>/generic_block_ai/reports/<report>.json
    return report_path.parent.parent.parent


def _resolve_report_path(project_root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _report_ref(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _diff_sets(baseline: set[str], candidate: set[str]) -> dict[str, list[str]]:
    return {
        "added": sorted(candidate - baseline),
        "removed": sorted(baseline - candidate),
        "common": sorted(baseline & candidate),
    }


def _load_ir20_pack_state(project_root: Path, ir20_bundle_report: dict[str, Any]) -> tuple[set[str], dict[str, str], list[str]]:
    failures: list[str] = []

    manifest_rel = str(ir20_bundle_report.get("manifest_path", ""))
    sha_rel = str(ir20_bundle_report.get("sha256_manifest_path", ""))

    manifest_path = _resolve_report_path(project_root, manifest_rel)
    sha_path = _resolve_report_path(project_root, sha_rel)

    if not manifest_path.exists():
        failures.append(f"ir20 manifest not found: {manifest_path}")
    if not sha_path.exists():
        failures.append(f"ir20 sha256 manifest not found: {sha_path}")

    if failures:
        return set(), {}, failures

    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != IR20_SCHEMA_VERSION:
        failures.append(f"ir20 manifest schema_version must be {IR20_SCHEMA_VERSION}")

    included = manifest.get("included_artifacts", []) if isinstance(manifest.get("included_artifacts"), list) else []
    sha_manifest = _read_json(sha_path)
    normalized_sha = {
        str(k): str(v) for k, v in sha_manifest.items()
    } if isinstance(sha_manifest, dict) else {}

    return set(str(x) for x in included), normalized_sha, failures


def _load_profile_selection_state(
    project_root: Path,
    profile_report_path: Path,
) -> tuple[str, set[str], dict[str, str], list[str]]:
    failures: list[str] = []

    if not profile_report_path.exists():
        return "unknown", set(), {}, [f"profile report not found: {profile_report_path}"]

    profile_report = _read_json(profile_report_path)
    if profile_report.get("schema_version") != IR22_SCHEMA_VERSION:
        failures.append(f"profile report schema_version must be {IR22_SCHEMA_VERSION}: {profile_report_path}")

    profile_name = str(profile_report.get("profile_name", "unknown"))
    profile_manifest_rel = str(profile_report.get("profile_manifest_path", ""))
    selected_sha_rel = str(profile_report.get("selected_sha256_manifest_path", ""))

    profile_manifest_path = _resolve_report_path(project_root, profile_manifest_rel)
    selected_sha_path = _resolve_report_path(project_root, selected_sha_rel)

    if not profile_manifest_path.exists():
        failures.append(f"profile manifest not found: {profile_manifest_path}")
    if not selected_sha_path.exists():
        failures.append(f"selected sha256 manifest not found: {selected_sha_path}")

    if failures:
        return profile_name, set(), {}, failures

    profile_manifest = _read_json(profile_manifest_path)
    selected = profile_manifest.get("selected_artifacts", []) if isinstance(profile_manifest.get("selected_artifacts"), list) else []

    selected_sha = _read_json(selected_sha_path)
    normalized_sha = {
        str(k): str(v) for k, v in selected_sha.items()
    } if isinstance(selected_sha, dict) else {}

    return profile_name, set(str(x) for x in selected), normalized_sha, failures


def run_ir24_submission_version_diff_audit_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    baseline_ir23_report_path: Path | None = None,
    candidate_ir23_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR24-T1/T2/T3/T4
    Compare baseline and candidate submission lifecycle reports and fix traceability deltas.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    baseline_path = baseline_ir23_report_path or (reports_dir / "ir23_evidence_pack_lifecycle_audit_report_ir23_live_trial.json")
    candidate_path = candidate_ir23_report_path or (reports_dir / "ir23_evidence_pack_lifecycle_audit_report_ir23_resubmission_trial.json")

    failures: list[str] = []
    warnings: list[str] = []

    if not baseline_path.exists():
        failures.append(f"baseline ir23 report not found: {baseline_path}")
    if not candidate_path.exists():
        failures.append(f"candidate ir23 report not found: {candidate_path}")

    bundle_diff: dict[str, Any] = {}
    profile_diff: dict[str, Any] = {}

    if not failures:
        baseline_ir23 = _read_json(baseline_path)
        candidate_ir23 = _read_json(candidate_path)

        for label, report in [("baseline", baseline_ir23), ("candidate", candidate_ir23)]:
            if report.get("schema_version") != IR23_SCHEMA_VERSION:
                failures.append(f"{label} ir23 schema_version must be {IR23_SCHEMA_VERSION}")
            if report.get("validation_result") != "PASS":
                failures.append(f"{label} ir23 validation_result must be PASS")

        baseline_trace = baseline_ir23.get("traceability", {}) if isinstance(baseline_ir23.get("traceability"), dict) else {}
        candidate_trace = candidate_ir23.get("traceability", {}) if isinstance(candidate_ir23.get("traceability"), dict) else {}
        baseline_root = _project_root_from_report(baseline_path)
        candidate_root = _project_root_from_report(candidate_path)

        baseline_bundle_path = _resolve_report_path(baseline_root, str(baseline_trace.get("ir20_bundle_report", "")))
        candidate_bundle_path = _resolve_report_path(candidate_root, str(candidate_trace.get("ir20_bundle_report", "")))

        if not baseline_bundle_path.exists():
            failures.append(f"baseline ir20 bundle report not found: {baseline_bundle_path}")
        if not candidate_bundle_path.exists():
            failures.append(f"candidate ir20 bundle report not found: {candidate_bundle_path}")

        baseline_profile_reports = [
            _resolve_report_path(baseline_root, str(p))
            for p in baseline_trace.get("ir22_profile_reports", [])
            if isinstance(baseline_trace.get("ir22_profile_reports"), list)
        ]
        candidate_profile_reports = [
            _resolve_report_path(candidate_root, str(p))
            for p in candidate_trace.get("ir22_profile_reports", [])
            if isinstance(candidate_trace.get("ir22_profile_reports"), list)
        ]

        if not baseline_profile_reports:
            failures.append("baseline ir23 has no ir22 profile reports")
        if not candidate_profile_reports:
            failures.append("candidate ir23 has no ir22 profile reports")

        if not failures:
            baseline_bundle = _read_json(baseline_bundle_path)
            candidate_bundle = _read_json(candidate_bundle_path)

            if baseline_bundle.get("schema_version") != IR20_SCHEMA_VERSION:
                failures.append(f"baseline ir20 bundle schema_version must be {IR20_SCHEMA_VERSION}")
            if candidate_bundle.get("schema_version") != IR20_SCHEMA_VERSION:
                failures.append(f"candidate ir20 bundle schema_version must be {IR20_SCHEMA_VERSION}")

            baseline_included, baseline_sha, baseline_pack_failures = _load_ir20_pack_state(baseline_root, baseline_bundle)
            candidate_included, candidate_sha, candidate_pack_failures = _load_ir20_pack_state(candidate_root, candidate_bundle)
            failures.extend(baseline_pack_failures)
            failures.extend(candidate_pack_failures)

            if not failures:
                set_diff = _diff_sets(baseline_included, candidate_included)
                common_artifacts = set_diff["common"]
                sha_changed = [
                    rel for rel in common_artifacts
                    if baseline_sha.get(rel) != candidate_sha.get(rel)
                ]
                bundle_diff = {
                    "artifact_set": {
                        "added": set_diff["added"],
                        "removed": set_diff["removed"],
                        "common_count": len(common_artifacts),
                    },
                    "sha256_changed": sorted(sha_changed),
                    "sha256_changed_count": len(sha_changed),
                }

                baseline_profiles: dict[str, dict[str, Any]] = {}
                candidate_profiles: dict[str, dict[str, Any]] = {}

                for report_path in baseline_profile_reports:
                    profile_name, selected, selected_sha, profile_failures = _load_profile_selection_state(baseline_root, report_path)
                    failures.extend(profile_failures)
                    baseline_profiles[profile_name] = {
                        "selected": selected,
                        "sha": selected_sha,
                        "report": _report_ref(report_path, baseline_root) if report_path.exists() else str(report_path),
                    }

                for report_path in candidate_profile_reports:
                    profile_name, selected, selected_sha, profile_failures = _load_profile_selection_state(candidate_root, report_path)
                    failures.extend(profile_failures)
                    candidate_profiles[profile_name] = {
                        "selected": selected,
                        "sha": selected_sha,
                        "report": _report_ref(report_path, candidate_root) if report_path.exists() else str(report_path),
                    }

                baseline_profile_names = set(baseline_profiles.keys())
                candidate_profile_names = set(candidate_profiles.keys())
                profile_set_diff = _diff_sets(baseline_profile_names, candidate_profile_names)

                per_profile: list[dict[str, Any]] = []
                for profile_name in sorted(baseline_profile_names & candidate_profile_names):
                    b_selected = baseline_profiles[profile_name]["selected"]
                    c_selected = candidate_profiles[profile_name]["selected"]
                    selected_set_diff = _diff_sets(b_selected, c_selected)
                    common_selected = selected_set_diff["common"]

                    b_sha = baseline_profiles[profile_name]["sha"]
                    c_sha = candidate_profiles[profile_name]["sha"]
                    sha_changed = [
                        rel for rel in common_selected
                        if b_sha.get(rel) != c_sha.get(rel)
                    ]

                    per_profile.append(
                        {
                            "profile_name": profile_name,
                            "selected_artifact_set": {
                                "added": selected_set_diff["added"],
                                "removed": selected_set_diff["removed"],
                                "common_count": len(common_selected),
                            },
                            "sha256_changed": sorted(sha_changed),
                            "sha256_changed_count": len(sha_changed),
                            "baseline_report": baseline_profiles[profile_name]["report"],
                            "candidate_report": candidate_profiles[profile_name]["report"],
                        }
                    )

                profile_diff = {
                    "profile_set": {
                        "added": profile_set_diff["added"],
                        "removed": profile_set_diff["removed"],
                        "common_count": len(profile_set_diff["common"]),
                    },
                    "profiles": per_profile,
                }

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR24_SCHEMA_VERSION,
        "phase": "IR24",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "bundle_added_artifact_count": len(bundle_diff.get("artifact_set", {}).get("added", [])),
            "bundle_removed_artifact_count": len(bundle_diff.get("artifact_set", {}).get("removed", [])),
            "bundle_sha256_changed_count": int(bundle_diff.get("sha256_changed_count", 0)),
            "profile_added_count": len(profile_diff.get("profile_set", {}).get("added", [])),
            "profile_removed_count": len(profile_diff.get("profile_set", {}).get("removed", [])),
            "profiles_compared": len(profile_diff.get("profiles", [])),
            "failed_check_count": len(failures),
            "warning_count": len(warnings),
        },
        "diff_audit": {
            "baseline_ir23_report": _report_ref(baseline_path, project_root) if baseline_path.exists() else str(baseline_path),
            "candidate_ir23_report": _report_ref(candidate_path, project_root) if candidate_path.exists() else str(candidate_path),
            "bundle_diff": bundle_diff,
            "profile_diff": profile_diff,
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir24_submission_version_diff_audit_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "diff_report": report,
        "external_write_executed": False,
    }


def write_ir24_completion_report(
    *,
    base_path: Path,
    ir24_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR24-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    diff_report = ir24_output.get("diff_report", {}) if isinstance(ir24_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 24",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR24_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": diff_report.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(diff_report.get("validation_failed_checks", [])),
        "validation_warning_count": len(diff_report.get("validation_warnings", [])),
        "summary": diff_report.get("summary", {}),
        "artifacts": {
            "diff_report": ir24_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase24_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase24_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

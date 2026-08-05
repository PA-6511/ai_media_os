"""
core_submission_profile_builder.py - IR22

Build submission-target profiles from IR20 evidence pack artifacts.
Profiles select only required artifacts and produce profile-specific manifest/sha256.
"""
from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR20_SCHEMA_VERSION = "ir20_cross_phase_evidence_bundle_v1"
IR21_SCHEMA_VERSION = "ir21_evidence_pack_verifier_v1"
IR22_SCHEMA_VERSION = "ir22_submission_profile_v1"

PROFILE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "audit_submission": {
        "description": "Full audit submission profile with all completion reports and core logs.",
        "required_patterns": [
            "generic_block_ai/reports/implementation_restart_phase1[2-9]_completion_report.json",
            "generic_block_ai/reports/ir12_core_decision_queue_audit.log",
            "generic_block_ai/reports/ir13_manual_approval_audit.log",
            "generic_block_ai/reports/ir17_role_policy_change_audit.log",
            "generic_block_ai/reports/ir19_policy_drift_detector_report_*.json",
        ],
    },
    "review_minimal": {
        "description": "Compact reviewer profile focused on final gate reports.",
        "required_patterns": [
            "generic_block_ai/reports/implementation_restart_phase1[89]_completion_report.json",
            "generic_block_ai/reports/ir17_role_policy_versioning_report_*.json",
            "generic_block_ai/reports/ir19_policy_drift_detector_report_*.json",
        ],
    },
    "policy_focus": {
        "description": "Policy and role governance review profile.",
        "required_patterns": [
            "generic_block_ai/reports/implementation_restart_phase15_completion_report.json",
            "generic_block_ai/reports/implementation_restart_phase17_completion_report.json",
            "generic_block_ai/reports/implementation_restart_phase19_completion_report.json",
            "generic_block_ai/reports/ir15_manual_event_role_guard_*.json",
            "generic_block_ai/reports/ir17_role_policy_change_audit.log",
            "generic_block_ai/reports/ir17_role_policy_versioning_report_*.json",
            "generic_block_ai/reports/ir19_policy_drift_detector_report_*.json",
        ],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _select_by_patterns(candidates: list[str], patterns: list[str]) -> list[str]:
    selected: set[str] = set()
    for pattern in patterns:
        for candidate in candidates:
            if fnmatch.fnmatch(candidate, pattern):
                selected.add(candidate)
    return sorted(selected)


def _write_readme(path: Path, profile_name: str, selected_count: int, missing_count: int) -> None:
    lines = [
        f"# IR22 Submission Profile: {profile_name}",
        "",
        "Generated in dry-run mode.",
        f"- Selected artifacts: {selected_count}",
        f"- Missing required pattern matches: {missing_count}",
        "- External write: false",
        "- Production release: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir22_submission_profile_builder_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    profile_name: str,
    ir20_bundle_report_path: Path | None = None,
    ir21_verifier_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR22-T1/T2/T3/T4
    Build one submission profile from IR20 evidence pack and verify gate prerequisites.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    if profile_name not in PROFILE_DEFINITIONS:
        raise ValueError(f"unknown profile_name: {profile_name}")

    bundle_report_path = ir20_bundle_report_path or (reports_dir / "ir20_cross_phase_evidence_bundle_ir20_live_trial.json")
    verifier_report_path = ir21_verifier_report_path or (reports_dir / "ir21_evidence_pack_verifier_report_ir21_live_trial.json")

    failures: list[str] = []
    warnings: list[str] = []

    if not bundle_report_path.exists():
        failures.append(f"ir20 bundle report not found: {bundle_report_path}")
    if not verifier_report_path.exists():
        failures.append(f"ir21 verifier report not found: {verifier_report_path}")

    if failures:
        validation_result = "FAIL"
        selected_artifacts: list[str] = []
        selected_sha256: dict[str, str] = {}
        missing_patterns: list[str] = []
    else:
        bundle_report = _read_json(bundle_report_path)
        verifier_report = _read_json(verifier_report_path)

        if bundle_report.get("validation_result") != "PASS":
            failures.append("ir20 bundle validation_result must be PASS")
        if verifier_report.get("validation_result") != "PASS":
            failures.append("ir21 verifier validation_result must be PASS")

        manifest_rel = str(bundle_report.get("manifest_path", ""))
        sha_rel = str(bundle_report.get("sha256_manifest_path", ""))
        manifest_path = project_root / manifest_rel
        sha_path = project_root / sha_rel

        if not manifest_path.exists():
            failures.append(f"ir20 manifest not found: {manifest_path}")
        if not sha_path.exists():
            failures.append(f"ir20 sha256 manifest not found: {sha_path}")

        selected_artifacts = []
        selected_sha256 = {}
        missing_patterns = []

        if not failures:
            manifest = _read_json(manifest_path)
            sha_manifest = _read_json(sha_path)

            if manifest.get("schema_version") != IR20_SCHEMA_VERSION:
                failures.append(f"ir20 manifest schema_version must be {IR20_SCHEMA_VERSION}")
            if verifier_report.get("schema_version") != IR21_SCHEMA_VERSION:
                failures.append(f"ir21 verifier schema_version must be {IR21_SCHEMA_VERSION}")

            available = manifest.get("included_artifacts", []) if isinstance(manifest.get("included_artifacts"), list) else []
            patterns = PROFILE_DEFINITIONS[profile_name]["required_patterns"]
            selected_artifacts = _select_by_patterns(available, patterns)

            for pattern in patterns:
                if not any(fnmatch.fnmatch(path, pattern) for path in available):
                    missing_patterns.append(pattern)

            for rel in selected_artifacts:
                if rel not in sha_manifest:
                    failures.append(f"selected artifact missing sha256 entry: {rel}")
                else:
                    selected_sha256[rel] = str(sha_manifest[rel])

            if missing_patterns:
                warnings.append(f"profile patterns not matched: {missing_patterns}")

        validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    profile_dir = reports_dir / f"ir22_submission_profile_{_safe(profile_name)}_{_safe(source_task_id)}"
    profile_dir.mkdir(parents=True, exist_ok=True)

    profile_manifest = {
        "schema_version": IR22_SCHEMA_VERSION,
        "phase": "IR22",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "profile_name": profile_name,
        "profile_description": PROFILE_DEFINITIONS[profile_name]["description"],
        "required_patterns": PROFILE_DEFINITIONS[profile_name]["required_patterns"],
        "selected_artifacts": selected_artifacts,
        "missing_patterns": missing_patterns,
        "counts": {
            "selected": len(selected_artifacts),
            "missing_patterns": len(missing_patterns),
        },
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    profile_manifest_path = profile_dir / "profile_manifest.json"
    selected_sha_path = profile_dir / "selected_sha256_manifest.json"
    readme_path = profile_dir / "README.md"

    profile_manifest_path.write_text(json.dumps(profile_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected_sha_path.write_text(json.dumps(selected_sha256, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readme(readme_path, profile_name, len(selected_artifacts), len(missing_patterns))

    report = {
        "schema_version": IR22_SCHEMA_VERSION,
        "phase": "IR22",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "profile_name": profile_name,
        "validation_result": validation_result,
        "selected_artifact_count": len(selected_artifacts),
        "missing_pattern_count": len(missing_patterns),
        "profile_dir": str(profile_dir.relative_to(project_root).as_posix()),
        "profile_manifest_path": str(profile_manifest_path.relative_to(project_root).as_posix()),
        "selected_sha256_manifest_path": str(selected_sha_path.relative_to(project_root).as_posix()),
        "readme_path": str(readme_path.relative_to(project_root).as_posix()),
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir22_submission_profile_report_{_safe(profile_name)}_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "profile_report": report,
        "external_write_executed": False,
    }


def write_ir22_completion_report(
    *,
    base_path: Path,
    ir22_outputs: list[dict[str, Any]],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR22-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    result_counts: dict[str, int] = {}
    profile_counts: dict[str, int] = {}
    artifact_paths: list[str] = []

    for output in ir22_outputs:
        if not isinstance(output, dict):
            continue
        artifact_paths.append(output.get("path", "UNKNOWN"))
        report = output.get("profile_report", {})
        result = str(report.get("validation_result", "UNKNOWN"))
        profile = str(report.get("profile_name", "UNKNOWN"))
        result_counts[result] = result_counts.get(result, 0) + 1
        profile_counts[profile] = profile_counts.get(profile, 0) + 1

    overall = "PASS"
    if result_counts.get("FAIL", 0) > 0:
        overall = "FAIL"
    elif result_counts.get("WARN", 0) > 0:
        overall = "WARN"

    completion = {
        "phase": "Implementation Restart Phase 22",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR22_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": overall,
        "summary": {
            "profile_result_counts": result_counts,
            "profile_counts": profile_counts,
            "reports_generated": len(artifact_paths),
        },
        "artifacts": {
            "profile_reports": artifact_paths,
            "completion_report": "reports/implementation_restart_phase22_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase22_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

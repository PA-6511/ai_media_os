"""
core_evidence_pack_verifier.py - IR21

Verify IR20 evidence packs before submission:
- manifest required fields
- sha256 manifest recomputation
- missing/tampered file detection
- README/completion report/bundle summary consistency
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR20_SCHEMA_VERSION = "ir20_cross_phase_evidence_bundle_v1"
IR21_SCHEMA_VERSION = "ir21_evidence_pack_verifier_v1"

_MANIFEST_REQUIRED_KEYS = {
    "schema_version",
    "phase",
    "generated_at",
    "source_task_id",
    "validation_result",
    "required_artifacts",
    "included_artifacts",
    "missing_required_artifacts",
    "counts",
    "safeguards",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _validate_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    missing_keys = sorted(key for key in _MANIFEST_REQUIRED_KEYS if key not in manifest)
    if missing_keys:
        failures.append(f"manifest missing keys: {missing_keys}")

    if manifest.get("schema_version") != IR20_SCHEMA_VERSION:
        failures.append(f"manifest.schema_version must be {IR20_SCHEMA_VERSION}")

    counts = manifest.get("counts", {}) if isinstance(manifest.get("counts"), dict) else {}
    required = manifest.get("required_artifacts", []) if isinstance(manifest.get("required_artifacts"), list) else []
    included = manifest.get("included_artifacts", []) if isinstance(manifest.get("included_artifacts"), list) else []
    missing_required = (
        manifest.get("missing_required_artifacts", [])
        if isinstance(manifest.get("missing_required_artifacts"), list)
        else []
    )

    if counts.get("required") != len(required):
        failures.append("manifest counts.required does not match required_artifacts length")
    if counts.get("included") != len(included):
        failures.append("manifest counts.included does not match included_artifacts length")
    if counts.get("missing_required") != len(missing_required):
        failures.append("manifest counts.missing_required does not match missing_required_artifacts length")

    return failures


def _verify_sha256_manifest(
    *,
    project_root: Path,
    included_artifacts: list[str],
    sha_manifest: dict[str, str],
) -> tuple[list[str], list[str], list[dict[str, str]]]:
    missing_files: list[str] = []
    missing_sha_entries: list[str] = []
    tampered_files: list[dict[str, str]] = []

    for rel in included_artifacts:
        abs_path = project_root / rel
        if not abs_path.exists() or not abs_path.is_file():
            missing_files.append(rel)
            continue

        expected = sha_manifest.get(rel)
        if not expected:
            missing_sha_entries.append(rel)
            continue

        actual = _sha256_file(abs_path)
        if actual != expected:
            tampered_files.append(
                {
                    "path": rel,
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                }
            )

    return missing_files, missing_sha_entries, tampered_files


def _verify_readme_consistency(
    *,
    readme_text: str,
    included_count: int,
    missing_required_count: int,
) -> list[str]:
    failures: list[str] = []
    included_line = f"- Included artifacts: {included_count}"
    missing_line = f"- Missing required artifacts: {missing_required_count}"

    if included_line not in readme_text:
        failures.append("README included artifacts count mismatch")
    if missing_line not in readme_text:
        failures.append("README missing required artifacts count mismatch")

    return failures


def run_ir21_evidence_pack_verifier_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    bundle_report_path: Path | None = None,
    completion_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR21-T1/T2/T3/T4
    Verify IR20 evidence pack integrity and consistency.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    project_root = _project_root_from_base(base_path)

    if bundle_report_path is None:
        default = reports_dir / "ir20_cross_phase_evidence_bundle_ir20_live_trial.json"
        bundle_report_path = default
    if completion_report_path is None:
        completion_report_path = reports_dir / "implementation_restart_phase20_completion_report.json"

    failures: list[str] = []
    warnings: list[str] = []

    if not bundle_report_path.exists():
        failures.append(f"bundle report not found: {bundle_report_path}")
    if not completion_report_path.exists():
        failures.append(f"completion report not found: {completion_report_path}")

    if failures:
        result = {
            "schema_version": IR21_SCHEMA_VERSION,
            "phase": "IR21",
            "generated_at": _now_iso(),
            "source_task_id": source_task_id,
            "validation_result": "FAIL",
            "validation_failed_checks": failures,
            "validation_warnings": warnings,
            "summary": {
                "manifest_checks": 0,
                "sha_checks": 0,
                "missing_files": 0,
                "tampered_files": 0,
                "readme_checks": 0,
                "completion_checks": 0,
            },
            "safeguards": {
                "mode": "dry_run",
                "operation_mode": "OBSERVE",
                "execution_policy_execute": False,
                "external_write_executed": False,
                "production_release": False,
            },
        }
        out = reports_dir / f"ir21_evidence_pack_verifier_report_{_safe(source_task_id)}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"path": str(out), "verifier_report": result, "external_write_executed": False}

    bundle = _read_json(bundle_report_path)

    manifest_rel = str(bundle.get("manifest_path", ""))
    sha_rel = str(bundle.get("sha256_manifest_path", ""))
    readme_rel = str(bundle.get("readme_path", ""))

    manifest_path = project_root / manifest_rel
    sha_path = project_root / sha_rel
    readme_path = project_root / readme_rel

    for label, path in [
        ("manifest", manifest_path),
        ("sha256_manifest", sha_path),
        ("readme", readme_path),
    ]:
        if not path.exists():
            failures.append(f"{label} file not found: {path}")

    if failures:
        validation_result = "FAIL"
        manifest = {}
        sha_manifest = {}
        readme_text = ""
    else:
        manifest = _read_json(manifest_path)
        sha_manifest = _read_json(sha_path)
        readme_text = readme_path.read_text(encoding="utf-8")

        failures.extend(_validate_manifest_schema(manifest))

        included_artifacts = (
            manifest.get("included_artifacts", []) if isinstance(manifest.get("included_artifacts"), list) else []
        )
        missing_files, missing_sha_entries, tampered_files = _verify_sha256_manifest(
            project_root=project_root,
            included_artifacts=included_artifacts,
            sha_manifest=sha_manifest if isinstance(sha_manifest, dict) else {},
        )

        if missing_files:
            failures.append(f"included artifacts missing on disk: {missing_files}")
        if missing_sha_entries:
            failures.append(f"sha256 entries missing for artifacts: {missing_sha_entries}")
        if tampered_files:
            failures.append("sha256 mismatch detected for one or more artifacts")

        failures.extend(
            _verify_readme_consistency(
                readme_text=readme_text,
                included_count=len(included_artifacts),
                missing_required_count=len(manifest.get("missing_required_artifacts", [])),
            )
        )

        completion = _read_json(completion_report_path)
        completion_artifacts = completion.get("artifacts", {}) if isinstance(completion.get("artifacts"), dict) else {}
        expected_bundle_rel = bundle_report_path.relative_to(project_root).as_posix()
        expected_bundle_abs = str(bundle_report_path.resolve())
        actual_bundle_value = str(completion_artifacts.get("bundle_report", ""))
        if actual_bundle_value not in {expected_bundle_rel, expected_bundle_abs}:
            failures.append("completion report bundle_report path mismatch")

        expected_manifest_rel = manifest_path.relative_to(project_root).as_posix()
        if str(completion_artifacts.get("manifest", "")) != expected_manifest_rel:
            failures.append("completion report manifest path mismatch")

        expected_sha_rel = sha_path.relative_to(project_root).as_posix()
        if str(completion_artifacts.get("sha256_manifest", "")) != expected_sha_rel:
            failures.append("completion report sha256_manifest path mismatch")

        validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    tampered_files_summary: list[dict[str, str]] = []
    if manifest and isinstance(manifest.get("included_artifacts"), list) and isinstance(sha_manifest, dict):
        _, _, tampered_files_summary = _verify_sha256_manifest(
            project_root=project_root,
            included_artifacts=manifest.get("included_artifacts", []),
            sha_manifest=sha_manifest,
        )

    report = {
        "schema_version": IR21_SCHEMA_VERSION,
        "phase": "IR21",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "manifest_checks": 1,
            "sha_checks": 1,
            "missing_files": len([f for f in failures if "missing" in f.lower()]),
            "tampered_files": len(tampered_files_summary),
            "readme_checks": 1,
            "completion_checks": 1,
        },
        "tampered_files": tampered_files_summary,
        "artifacts": {
            "bundle_report": str(bundle_report_path.relative_to(project_root).as_posix()),
            "manifest": manifest_rel,
            "sha256_manifest": sha_rel,
            "readme": readme_rel,
            "completion_report": str(completion_report_path.relative_to(project_root).as_posix()),
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir21_evidence_pack_verifier_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "verifier_report": report,
        "external_write_executed": False,
    }


def write_ir21_completion_report(
    *,
    base_path: Path,
    ir21_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR21-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    verifier = ir21_output.get("verifier_report", {}) if isinstance(ir21_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 21",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR21_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": verifier.get("validation_result", "UNKNOWN"),
        "validation_failed_check_count": len(verifier.get("validation_failed_checks", [])),
        "validation_warning_count": len(verifier.get("validation_warnings", [])),
        "summary": verifier.get("summary", {}),
        "artifacts": {
            "verifier_report": ir21_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase21_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase21_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

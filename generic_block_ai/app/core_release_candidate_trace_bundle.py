"""
core_release_candidate_trace_bundle.py - IR28

Build a release-candidate-scoped trace bundle by linking IR20-IR27 artifacts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR26_SCHEMA_VERSION = "ir26_submission_release_candidate_marker_v1"
IR27_SCHEMA_VERSION = "ir27_release_candidate_integrity_verifier_v1"
IR28_SCHEMA_VERSION = "ir28_release_candidate_trace_bundle_v1"


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


def _add_artifact(
    *,
    ref: str,
    project_root: Path,
    included: set[str],
    failures: list[str],
    required_label: str,
) -> Path | None:
    target = _resolve(project_root, ref)
    if not target.exists() or not target.is_file():
        failures.append(f"{required_label} not found: {target}")
        return None
    included.add(_to_ref(target, project_root))
    return target


def _write_readme(path: Path, release_candidate_id: str, included_count: int, missing_count: int) -> None:
    lines = [
        "# IR28 Release Candidate Trace Bundle",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Included artifacts: {included_count}",
        f"- Missing required artifacts: {missing_count}",
        "- External write: false",
        "- Production release: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir28_release_candidate_trace_bundle_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir27_integrity_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR28-T1/T2/T3/T4
    Build release-candidate-scoped trace bundle from IR27 -> IR20 chain.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    ir27_path = ir27_integrity_report_path or (reports_dir / "ir27_release_candidate_integrity_verifier_report_ir27_live_trial.json")

    failures: list[str] = []
    warnings: list[str] = []
    included_refs: set[str] = set()
    release_candidate_id = "UNKNOWN"
    trace_summary: dict[str, Any] = {
        "ir23_reports": 0,
        "ir22_profile_reports": 0,
        "phase_completion_reports": 0,
    }

    if not ir27_path.exists():
        failures.append(f"ir27 integrity report not found: {ir27_path}")

    if not failures:
        ir27 = _read_json(ir27_path)
        if ir27.get("schema_version") != IR27_SCHEMA_VERSION:
            failures.append(f"ir27 schema_version must be {IR27_SCHEMA_VERSION}")
        if ir27.get("validation_result") != "PASS":
            failures.append("ir27 validation_result must be PASS")

        release_candidate_id = str(ir27.get("release_candidate_id", "UNKNOWN"))
        included_refs.add(_to_ref(ir27_path, project_root))

        ir27_artifacts = ir27.get("artifacts", {}) if isinstance(ir27.get("artifacts"), dict) else {}
        ir26_ref = str(ir27_artifacts.get("ir26_marker_report", ""))
        ir26_path = _add_artifact(
            ref=ir26_ref,
            project_root=project_root,
            included=included_refs,
            failures=failures,
            required_label="ir26 marker report",
        ) if ir26_ref else None

        if ir26_path is not None and not failures:
            ir26 = _read_json(ir26_path)
            if ir26.get("schema_version") != IR26_SCHEMA_VERSION:
                failures.append(f"ir26 schema_version must be {IR26_SCHEMA_VERSION}")
            if ir26.get("marker_result") != "PASS":
                failures.append("ir26 marker_result must be PASS")
            if str(ir26.get("release_candidate_id", "")) != release_candidate_id:
                failures.append("release_candidate_id mismatch between ir27 and ir26")

            ir26_artifacts = ir26.get("artifacts", {}) if isinstance(ir26.get("artifacts"), dict) else {}
            for key in ["approval_snapshot", "immutable_marker", "readme"]:
                ref = str(ir26_artifacts.get(key, ""))
                if ref:
                    _add_artifact(
                        ref=ref,
                        project_root=project_root,
                        included=included_refs,
                        failures=failures,
                        required_label=f"ir26 artifact {key}",
                    )

            ir25_ref = str(ir26_artifacts.get("ir25_gate_report", ""))
            ir25_path = _add_artifact(
                ref=ir25_ref,
                project_root=project_root,
                included=included_refs,
                failures=failures,
                required_label="ir25 gate report",
            ) if ir25_ref else None

            if ir25_path is not None and not failures:
                ir25 = _read_json(ir25_path)
                ir25_artifacts = ir25.get("artifacts", {}) if isinstance(ir25.get("artifacts"), dict) else {}
                ir24_ref = str(ir25_artifacts.get("ir24_diff_report", ""))
                ir24_path = _add_artifact(
                    ref=ir24_ref,
                    project_root=project_root,
                    included=included_refs,
                    failures=failures,
                    required_label="ir24 diff report",
                ) if ir24_ref else None

                if ir24_path is not None and not failures:
                    ir24 = _read_json(ir24_path)
                    diff_audit = ir24.get("diff_audit", {}) if isinstance(ir24.get("diff_audit"), dict) else {}
                    ir23_refs = [
                        str(diff_audit.get("baseline_ir23_report", "")),
                        str(diff_audit.get("candidate_ir23_report", "")),
                    ]
                    seen_ir23: set[str] = set()

                    for ir23_ref in ir23_refs:
                        if not ir23_ref:
                            continue
                        ir23_path = _add_artifact(
                            ref=ir23_ref,
                            project_root=project_root,
                            included=included_refs,
                            failures=failures,
                            required_label="ir23 lifecycle report",
                        )
                        if ir23_path is None:
                            continue
                        ir23_key = _to_ref(ir23_path, project_root)
                        if ir23_key in seen_ir23:
                            continue
                        seen_ir23.add(ir23_key)

                        ir23 = _read_json(ir23_path)
                        trace = ir23.get("traceability", {}) if isinstance(ir23.get("traceability"), dict) else {}
                        for key in ["ir20_bundle_report", "ir21_verifier_report", "ir22_completion_report"]:
                            ref = str(trace.get(key, ""))
                            if ref:
                                _add_artifact(
                                    ref=ref,
                                    project_root=project_root,
                                    included=included_refs,
                                    failures=failures,
                                    required_label=f"ir23 traceability {key}",
                                )

                        profile_refs = trace.get("ir22_profile_reports", []) if isinstance(trace.get("ir22_profile_reports"), list) else []
                        for profile_ref in profile_refs:
                            _add_artifact(
                                ref=str(profile_ref),
                                project_root=project_root,
                                included=included_refs,
                                failures=failures,
                                required_label="ir22 profile report",
                            )
                        trace_summary["ir22_profile_reports"] += len(profile_refs)

                    trace_summary["ir23_reports"] = len(seen_ir23)

        for phase in range(20, 28):
            completion_ref = f"generic_block_ai/reports/implementation_restart_phase{phase}_completion_report.json"
            if _add_artifact(
                ref=completion_ref,
                project_root=project_root,
                included=included_refs,
                failures=failures,
                required_label=f"phase {phase} completion report",
            ) is not None:
                trace_summary["phase_completion_reports"] += 1

    validation_result = "FAIL" if failures else ("WARN" if warnings else "PASS")

    bundle_dir = reports_dir / f"ir28_release_candidate_trace_bundle_{_safe(source_task_id)}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    included_sorted = sorted(included_refs)
    sha_manifest: dict[str, str] = {}
    for ref in included_sorted:
        path = _resolve(project_root, ref)
        if path.exists() and path.is_file():
            sha_manifest[ref] = _sha256_file(path)

    manifest = {
        "schema_version": IR28_SCHEMA_VERSION,
        "phase": "IR28",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "validation_result": validation_result,
        "included_artifacts": included_sorted,
        "missing_required_artifacts": failures,
        "counts": {
            "included": len(included_sorted),
            "missing_required": len(failures),
        },
        "trace_summary": trace_summary,
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    manifest_path = bundle_dir / "trace_manifest.json"
    sha_path = bundle_dir / "trace_sha256_manifest.json"
    readme_path = bundle_dir / "README.md"

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sha_path.write_text(json.dumps(sha_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readme(readme_path, release_candidate_id, len(included_sorted), len(failures))

    report = {
        "schema_version": IR28_SCHEMA_VERSION,
        "phase": "IR28",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "release_candidate_id": release_candidate_id,
        "validation_result": validation_result,
        "validation_failed_checks": failures,
        "validation_warnings": warnings,
        "summary": {
            "included_artifact_count": len(included_sorted),
            "failed_check_count": len(failures),
            "warning_count": len(warnings),
            "trace_summary": trace_summary,
        },
        "artifacts": {
            "trace_bundle_dir": _to_ref(bundle_dir, project_root),
            "trace_manifest": _to_ref(manifest_path, project_root),
            "trace_sha256_manifest": _to_ref(sha_path, project_root),
            "readme": _to_ref(readme_path, project_root),
            "completion_report": "reports/implementation_restart_phase28_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir28_release_candidate_trace_bundle_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "trace_report": report,
        "external_write_executed": False,
    }


def write_ir28_completion_report(
    *,
    base_path: Path,
    ir28_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR28-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    trace = ir28_output.get("trace_report", {}) if isinstance(ir28_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 28",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR28_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": trace.get("validation_result", "UNKNOWN"),
        "release_candidate_id": trace.get("release_candidate_id", "UNKNOWN"),
        "validation_failed_check_count": len(trace.get("validation_failed_checks", [])),
        "validation_warning_count": len(trace.get("validation_warnings", [])),
        "summary": trace.get("summary", {}),
        "artifacts": {
            "trace_report": ir28_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase28_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase28_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

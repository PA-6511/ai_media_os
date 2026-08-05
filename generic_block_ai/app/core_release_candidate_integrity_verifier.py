"""
core_release_candidate_integrity_verifier.py - IR27

Verify integrity and traceability of IR26 release candidate markers.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR25_SCHEMA_VERSION = "ir25_submission_change_approval_gate_v1"
IR26_SCHEMA_VERSION = "ir26_submission_release_candidate_marker_v1"
IR27_SCHEMA_VERSION = "ir27_release_candidate_integrity_verifier_v1"


REQUIRED_IMMUTABLE_MARKER_KEYS = {
    "schema_version",
    "phase",
    "generated_at",
    "source_task_id",
    "release_candidate_id",
    "approval_snapshot_hash",
    "immutable",
    "safeguards",
}

REQUIRED_IMMUTABLE_KEYS = {
    "marker_locked",
    "mutation_policy",
    "marker_rewrite_allowed",
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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _match_path_ref(path_value: str, expected_path: Path, project_root: Path) -> bool:
    try:
        expected_rel = expected_path.relative_to(project_root).as_posix()
    except ValueError:
        expected_rel = None
    expected_abs = str(expected_path.resolve())
    if expected_rel:
        return path_value in {expected_rel, expected_abs}
    return path_value == expected_abs


def run_ir27_release_candidate_integrity_verifier_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir26_marker_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR27-T1/T2/T3/T4
    Verify hash, immutable marker fields, tamper resistance, and IR25/IR26 references.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    marker_report_path = ir26_marker_report_path or (reports_dir / "ir26_submission_release_candidate_marker_report_ir26_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    if not marker_report_path.exists():
        failed_checks.append(f"ir26 marker report not found: {marker_report_path}")

    recalculated_snapshot_hash = ""
    marker_snapshot_hash = ""
    release_candidate_id = "UNKNOWN"
    tamper_flags = {
        "snapshot_hash_mismatch": False,
        "immutable_policy_mismatch": False,
        "reference_mismatch": False,
    }

    if not failed_checks:
        marker_report = _read_json(marker_report_path)
        if marker_report.get("schema_version") != IR26_SCHEMA_VERSION:
            failed_checks.append(f"ir26 marker report schema_version must be {IR26_SCHEMA_VERSION}")

        artifacts = marker_report.get("artifacts", {}) if isinstance(marker_report.get("artifacts"), dict) else {}

        snapshot_path = _resolve(project_root, str(artifacts.get("approval_snapshot", "")))
        immutable_marker_path = _resolve(project_root, str(artifacts.get("immutable_marker", "")))
        ir25_gate_path = _resolve(project_root, str(artifacts.get("ir25_gate_report", "")))

        for label, path in [
            ("approval snapshot", snapshot_path),
            ("immutable marker", immutable_marker_path),
            ("ir25 gate report", ir25_gate_path),
        ]:
            if not path.exists():
                failed_checks.append(f"{label} not found: {path}")

        if not failed_checks:
            snapshot = _read_json(snapshot_path)
            immutable_marker = _read_json(immutable_marker_path)
            ir25_gate = _read_json(ir25_gate_path)

            if ir25_gate.get("schema_version") != IR25_SCHEMA_VERSION:
                failed_checks.append(f"ir25 gate report schema_version must be {IR25_SCHEMA_VERSION}")
            if immutable_marker.get("schema_version") != IR26_SCHEMA_VERSION:
                failed_checks.append(f"immutable marker schema_version must be {IR26_SCHEMA_VERSION}")
            if snapshot.get("schema_version") != IR26_SCHEMA_VERSION:
                failed_checks.append(f"approval snapshot schema_version must be {IR26_SCHEMA_VERSION}")

            recalculated_snapshot_hash = _sha256_text(_canonical_json(snapshot))
            marker_snapshot_hash = str(immutable_marker.get("approval_snapshot_hash", ""))
            if recalculated_snapshot_hash != marker_snapshot_hash:
                tamper_flags["snapshot_hash_mismatch"] = True
                failed_checks.append("approval_snapshot_hash mismatch")

            missing_marker_keys = sorted(k for k in REQUIRED_IMMUTABLE_MARKER_KEYS if k not in immutable_marker)
            if missing_marker_keys:
                failed_checks.append(f"immutable marker missing keys: {missing_marker_keys}")

            immutable = immutable_marker.get("immutable", {}) if isinstance(immutable_marker.get("immutable"), dict) else {}
            missing_immutable_keys = sorted(k for k in REQUIRED_IMMUTABLE_KEYS if k not in immutable)
            if missing_immutable_keys:
                failed_checks.append(f"immutable marker.immutable missing keys: {missing_immutable_keys}")

            if immutable.get("marker_locked") is not True:
                tamper_flags["immutable_policy_mismatch"] = True
                failed_checks.append("immutable marker_locked must be true")
            if immutable.get("mutation_policy") != "append_only_no_overwrite":
                tamper_flags["immutable_policy_mismatch"] = True
                failed_checks.append("immutable mutation_policy must be append_only_no_overwrite")
            if immutable.get("marker_rewrite_allowed") is not False:
                tamper_flags["immutable_policy_mismatch"] = True
                failed_checks.append("immutable marker_rewrite_allowed must be false")

            release_candidate_id = str(marker_report.get("release_candidate_id", "UNKNOWN"))
            if str(immutable_marker.get("release_candidate_id", "")) != release_candidate_id:
                tamper_flags["reference_mismatch"] = True
                failed_checks.append("release_candidate_id mismatch between marker report and immutable marker")

            if not release_candidate_id.startswith("rc_"):
                tamper_flags["reference_mismatch"] = True
                failed_checks.append("release_candidate_id format invalid")

            snapshot_ir25 = snapshot.get("ir25", {}) if isinstance(snapshot.get("ir25"), dict) else {}
            if snapshot_ir25.get("decision") != "ALLOW":
                tamper_flags["reference_mismatch"] = True
                failed_checks.append("approval snapshot ir25 decision must be ALLOW")

            snapshot_artifacts = snapshot_ir25.get("artifacts", {}) if isinstance(snapshot_ir25.get("artifacts"), dict) else {}
            gate_artifacts = ir25_gate.get("artifacts", {}) if isinstance(ir25_gate.get("artifacts"), dict) else {}
            if str(snapshot_artifacts.get("ir24_diff_report", "")) != str(gate_artifacts.get("ir24_diff_report", "")):
                tamper_flags["reference_mismatch"] = True
                failed_checks.append("snapshot ir25 artifacts.ir24_diff_report mismatch against ir25 gate")

            marker_report_ir25_ref = str(artifacts.get("ir25_gate_report", ""))
            if not _match_path_ref(marker_report_ir25_ref, ir25_gate_path, project_root):
                tamper_flags["reference_mismatch"] = True
                failed_checks.append("marker report ir25_gate_report reference mismatch")

    validation_result = "FAIL" if failed_checks else ("WARN" if warnings else "PASS")

    report = {
        "schema_version": IR27_SCHEMA_VERSION,
        "phase": "IR27",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "release_candidate_id": release_candidate_id,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "integrity": {
            "recalculated_approval_snapshot_hash": recalculated_snapshot_hash,
            "marker_approval_snapshot_hash": marker_snapshot_hash,
            "tamper_flags": tamper_flags,
        },
        "summary": {
            "validation_result": validation_result,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "tamper_detected": any(tamper_flags.values()),
        },
        "artifacts": {
            "ir26_marker_report": str(marker_report_path.relative_to(project_root).as_posix()) if marker_report_path.exists() else str(marker_report_path),
            "completion_report": "reports/implementation_restart_phase27_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir27_release_candidate_integrity_verifier_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "integrity_report": report,
        "external_write_executed": False,
    }


def write_ir27_completion_report(
    *,
    base_path: Path,
    ir27_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR27-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    integrity = ir27_output.get("integrity_report", {}) if isinstance(ir27_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 27",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR27_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": integrity.get("validation_result", "UNKNOWN"),
        "release_candidate_id": integrity.get("release_candidate_id", "UNKNOWN"),
        "validation_failed_check_count": len(integrity.get("validation_failed_checks", [])),
        "validation_warning_count": len(integrity.get("validation_warnings", [])),
        "summary": integrity.get("summary", {}),
        "artifacts": {
            "integrity_report": ir27_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase27_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase27_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

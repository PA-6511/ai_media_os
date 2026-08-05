"""
core_submission_release_candidate_marker.py - IR26

Create immutable release candidate markers for submissions approved by IR25.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR25_SCHEMA_VERSION = "ir25_submission_change_approval_gate_v1"
IR26_SCHEMA_VERSION = "ir26_submission_release_candidate_marker_v1"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _write_readme(path: Path, release_candidate_id: str, marker_result: str) -> None:
    lines = [
        "# IR26 Submission Release Candidate Marker",
        "",
        f"- Release Candidate ID: {release_candidate_id}",
        f"- Marker Result: {marker_result}",
        "- Immutable marker lock: true",
        "- External write: false",
        "- Production release: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir26_submission_release_candidate_marker_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir25_gate_report_path: Path | None = None,
) -> dict[str, Any]:
    """
    IR26-T1/T2/T3/T4
    Create release candidate marker and approval snapshot when IR25 gate is ALLOW.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    gate_path = ir25_gate_report_path or (reports_dir / "ir25_submission_change_approval_gate_report_ir25_live_trial.json")

    failed_checks: list[str] = []
    warnings: list[str] = []

    marker_result = "FAIL"
    release_candidate_id = "UNKNOWN"
    approval_snapshot: dict[str, Any] = {}
    immutable_marker: dict[str, Any] = {}

    if not gate_path.exists():
        failed_checks.append(f"ir25 gate report not found: {gate_path}")
    else:
        gate = _read_json(gate_path)

        if gate.get("schema_version") != IR25_SCHEMA_VERSION:
            failed_checks.append(f"ir25 schema_version must be {IR25_SCHEMA_VERSION}")

        decision = str(gate.get("decision", ""))
        if decision != "ALLOW":
            failed_checks.append(f"ir25 decision must be ALLOW, got: {decision}")

        if not failed_checks:
            snapshot_created_at = _now_iso()
            approval_snapshot = {
                "schema_version": IR26_SCHEMA_VERSION,
                "phase": "IR26",
                "snapshot_created_at": snapshot_created_at,
                "source_task_id": source_task_id,
                "ir25": {
                    "decision": decision,
                    "decision_reasons": gate.get("decision_reasons", []),
                    "summary": gate.get("summary", {}),
                    "policy": gate.get("policy", {}),
                    "artifacts": gate.get("artifacts", {}),
                },
                "safeguards": {
                    "mode": "dry_run",
                    "operation_mode": "OBSERVE",
                    "execution_policy_execute": False,
                    "external_write_executed": False,
                    "production_release": False,
                },
            }

            approval_snapshot_hash = _sha256_text(_canonical_json(approval_snapshot))
            ts = _now_utc().strftime("%Y%m%dT%H%M%SZ")
            release_candidate_id = f"rc_{ts}_{_safe(source_task_id)}_{approval_snapshot_hash[:12]}"

            immutable_marker = {
                "schema_version": IR26_SCHEMA_VERSION,
                "phase": "IR26",
                "generated_at": _now_iso(),
                "source_task_id": source_task_id,
                "release_candidate_id": release_candidate_id,
                "approval_snapshot_hash": approval_snapshot_hash,
                "immutable": {
                    "marker_locked": True,
                    "mutation_policy": "append_only_no_overwrite",
                    "marker_rewrite_allowed": False,
                },
                "safeguards": {
                    "mode": "dry_run",
                    "operation_mode": "OBSERVE",
                    "execution_policy_execute": False,
                    "external_write_executed": False,
                    "production_release": False,
                },
            }
            marker_result = "PASS"

    marker_dir = reports_dir / f"ir26_release_candidate_marker_{_safe(source_task_id)}"
    marker_dir.mkdir(parents=True, exist_ok=True)

    approval_snapshot_path = marker_dir / "approval_snapshot.json"
    immutable_marker_path = marker_dir / "immutable_marker.json"
    readme_path = marker_dir / "README.md"

    approval_snapshot_path.write_text(json.dumps(approval_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    immutable_marker_path.write_text(json.dumps(immutable_marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readme(readme_path, release_candidate_id, marker_result)

    report = {
        "schema_version": IR26_SCHEMA_VERSION,
        "phase": "IR26",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "marker_result": marker_result,
        "release_candidate_id": release_candidate_id,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "summary": {
            "marker_result": marker_result,
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "immutable_marker_locked": bool(immutable_marker.get("immutable", {}).get("marker_locked", False)),
        },
        "artifacts": {
            "ir25_gate_report": str(gate_path.relative_to(project_root).as_posix()) if gate_path.exists() else str(gate_path),
            "marker_dir": str(marker_dir.relative_to(project_root).as_posix()),
            "approval_snapshot": str(approval_snapshot_path.relative_to(project_root).as_posix()),
            "immutable_marker": str(immutable_marker_path.relative_to(project_root).as_posix()),
            "readme": str(readme_path.relative_to(project_root).as_posix()),
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir26_submission_release_candidate_marker_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "marker_report": report,
        "external_write_executed": False,
    }


def write_ir26_completion_report(
    *,
    base_path: Path,
    ir26_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR26-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    marker = ir26_output.get("marker_report", {}) if isinstance(ir26_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 26",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR26_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "marker_result": marker.get("marker_result", "UNKNOWN"),
        "release_candidate_id": marker.get("release_candidate_id", "UNKNOWN"),
        "validation_failed_check_count": len(marker.get("validation_failed_checks", [])),
        "validation_warning_count": len(marker.get("validation_warnings", [])),
        "summary": marker.get("summary", {}),
        "artifacts": {
            "marker_report": ir26_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase26_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase26_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

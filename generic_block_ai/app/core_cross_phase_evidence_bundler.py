"""
core_cross_phase_evidence_bundler.py - IR20

Bundle IR12-IR19 artifacts into a single evidence pack with fixed manifest
and sha256 records for audit and review.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR20_SCHEMA_VERSION = "ir20_cross_phase_evidence_bundle_v1"

DEFAULT_REQUIRED_ARTIFACTS: list[str] = [
    "generic_block_ai/reports/implementation_restart_phase12_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase13_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase14_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase15_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase16_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase17_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase18_completion_report.json",
    "generic_block_ai/reports/implementation_restart_phase19_completion_report.json",
    "generic_block_ai/reports/ir12_core_decision_queue_audit.log",
    "generic_block_ai/reports/ir13_manual_approval_audit.log",
    "generic_block_ai/reports/ir17_role_policy_change_audit.log",
    "generic_block_ai/reports/ir19_policy_drift_detector_report_ir19_live_trial.json",
]

DEFAULT_OPTIONAL_GLOBS: list[str] = [
    "ir12_core_decision_queue_*.json",
    "ir13_manual_approval_event_*.json",
    "ir14_audit_log_integrity_report_*.json",
    "ir15_manual_event_role_guard_*.json",
    "ir16_audit_replay_report_*.json",
    "ir17_role_policy_versioning_report_*.json",
    "ir18_multistep_replay_consistency_report_*.json",
    "ir19_policy_drift_detector_report_*.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


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
    # Expected base path: <project_root>/generic_block_ai
    return base_path.parent


def _collect_optional_artifacts(base_path: Path, globs: list[str]) -> list[str]:
    reports_dir = base_path / "reports"
    collected: set[str] = set()
    for pattern in globs:
        for path in reports_dir.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(_project_root_from_base(base_path)).as_posix()
            collected.add(rel)
    return sorted(collected)


def _write_readme(path: Path, pack_name: str, included_count: int, missing_count: int) -> None:
    lines = [
        f"# {pack_name}",
        "",
        "This evidence pack is generated in dry-run mode.",
        "",
        f"- Included artifacts: {included_count}",
        f"- Missing required artifacts: {missing_count}",
        "- External write: false",
        "- Production release: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ir20_cross_phase_evidence_bundler_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    required_artifacts: list[str] | None = None,
    optional_globs: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR20-T1/T2/T3/T4
    Build one evidence pack for IR12-IR19 with fixed manifest and sha256 map.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    project_root = _project_root_from_base(base_path)
    required = required_artifacts or list(DEFAULT_REQUIRED_ARTIFACTS)
    optional = _collect_optional_artifacts(base_path, optional_globs or list(DEFAULT_OPTIONAL_GLOBS))

    candidate_paths = sorted(set(required + optional))

    included: list[str] = []
    missing_required: list[str] = []
    sha256_manifest: dict[str, str] = {}

    required_set = set(required)

    for rel in candidate_paths:
        abs_path = project_root / rel
        if not abs_path.exists() or not abs_path.is_file():
            if rel in required_set:
                missing_required.append(rel)
            continue
        included.append(rel)
        sha256_manifest[rel] = _sha256_file(abs_path)

    validation_result = "FAIL" if missing_required else "PASS"

    pack_name = f"ir20_evidence_pack_{_safe(source_task_id)}"
    pack_dir = reports_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": IR20_SCHEMA_VERSION,
        "phase": "IR20",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "required_artifacts": sorted(required),
        "included_artifacts": included,
        "missing_required_artifacts": missing_required,
        "counts": {
            "required": len(required),
            "included": len(included),
            "missing_required": len(missing_required),
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    manifest_path = pack_dir / "manifest.json"
    sha256_path = pack_dir / "sha256_manifest.json"
    readme_path = pack_dir / "README.md"

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sha256_path.write_text(json.dumps(sha256_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_readme(readme_path, pack_name, len(included), len(missing_required))

    bundle_report = {
        "schema_version": IR20_SCHEMA_VERSION,
        "phase": "IR20",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "validation_result": validation_result,
        "pack_dir": str(pack_dir.relative_to(project_root).as_posix()),
        "manifest_path": str(manifest_path.relative_to(project_root).as_posix()),
        "sha256_manifest_path": str(sha256_path.relative_to(project_root).as_posix()),
        "readme_path": str(readme_path.relative_to(project_root).as_posix()),
        "included_artifact_count": len(included),
        "missing_required_artifact_count": len(missing_required),
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    bundle_report_path = reports_dir / f"ir20_cross_phase_evidence_bundle_{_safe(source_task_id)}.json"
    bundle_report_path.write_text(json.dumps(bundle_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(bundle_report_path),
        "bundle_report": bundle_report,
        "manifest_path": str(manifest_path),
        "sha256_manifest_path": str(sha256_path),
        "external_write_executed": False,
    }


def write_ir20_completion_report(
    *,
    base_path: Path,
    ir20_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR20-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    bundle = ir20_output.get("bundle_report", {}) if isinstance(ir20_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 20",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR20_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "validation_result": bundle.get("validation_result", "UNKNOWN"),
        "included_artifact_count": bundle.get("included_artifact_count", 0),
        "missing_required_artifact_count": bundle.get("missing_required_artifact_count", 0),
        "artifacts": {
            "bundle_report": ir20_output.get("path", "UNKNOWN"),
            "manifest": bundle.get("manifest_path", "UNKNOWN"),
            "sha256_manifest": bundle.get("sha256_manifest_path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase20_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase20_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

"""
core_submission_change_approval_gate.py - IR25

Evaluate IR24 submission diff reports and classify resubmission changes into:
- ALLOW
- HUMAN_APPROVAL_REQUIRED
- REJECT
- ABORT
"""
from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IR24_SCHEMA_VERSION = "ir24_submission_version_diff_audit_v1"
IR25_SCHEMA_VERSION = "ir25_submission_change_approval_gate_v1"

DECISION_ALLOW = "ALLOW"
DECISION_HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
DECISION_REJECT = "REJECT"
DECISION_ABORT = "ABORT"

DEFAULT_ALLOWED_ADDITION_PATTERNS = [
    "generic_block_ai/reports/ir19_policy_drift_detector_report_*.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return normalized or "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root_from_base(base_path: Path) -> Path:
    return base_path.parent


def _all_match_allowed(paths: list[str], patterns: list[str]) -> bool:
    for path in paths:
        if not any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
            return False
    return True


def _flatten_profile_deltas(profile_diff: dict[str, Any], key: str) -> list[str]:
    values: list[str] = []
    profiles = profile_diff.get("profiles", []) if isinstance(profile_diff.get("profiles"), list) else []
    for item in profiles:
        if not isinstance(item, dict):
            continue
        if key == "selected_added":
            selected = item.get("selected_artifact_set", {}) if isinstance(item.get("selected_artifact_set"), dict) else {}
            added = selected.get("added", []) if isinstance(selected.get("added"), list) else []
            values.extend(str(x) for x in added)
        elif key == "selected_removed":
            selected = item.get("selected_artifact_set", {}) if isinstance(item.get("selected_artifact_set"), dict) else {}
            removed = selected.get("removed", []) if isinstance(selected.get("removed"), list) else []
            values.extend(str(x) for x in removed)
        elif key == "sha_changed":
            changed = item.get("sha256_changed", []) if isinstance(item.get("sha256_changed"), list) else []
            values.extend(str(x) for x in changed)
    return sorted(set(values))


def run_ir25_submission_change_approval_gate_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    ir24_diff_report_path: Path | None = None,
    allowed_addition_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """
    IR25-T1/T2/T3/T4
    Gate submission changes based on IR24 diff audit report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_from_base(base_path)

    diff_path = ir24_diff_report_path or (reports_dir / "ir24_submission_version_diff_audit_report_ir24_live_trial.json")
    policy_patterns = allowed_addition_patterns or list(DEFAULT_ALLOWED_ADDITION_PATTERNS)

    failed_checks: list[str] = []
    warnings: list[str] = []

    if not diff_path.exists():
        failed_checks.append(f"ir24 diff report not found: {diff_path}")

    decision = DECISION_ABORT
    decision_reasons: list[str] = []

    delta_summary: dict[str, Any] = {
        "bundle_added": [],
        "bundle_removed": [],
        "bundle_sha_changed": [],
        "profile_added": [],
        "profile_removed": [],
        "profile_selected_added": [],
        "profile_selected_removed": [],
        "profile_sha_changed": [],
    }

    if not failed_checks:
        ir24 = _read_json(diff_path)

        if ir24.get("schema_version") != IR24_SCHEMA_VERSION:
            failed_checks.append(f"ir24 schema_version must be {IR24_SCHEMA_VERSION}")
        if ir24.get("validation_result") != "PASS":
            failed_checks.append("ir24 validation_result must be PASS")

        if failed_checks:
            decision = DECISION_ABORT
            decision_reasons.append("prerequisite_ir24_not_valid")
        else:
            diff_audit = ir24.get("diff_audit", {}) if isinstance(ir24.get("diff_audit"), dict) else {}
            bundle_diff = diff_audit.get("bundle_diff", {}) if isinstance(diff_audit.get("bundle_diff"), dict) else {}
            profile_diff = diff_audit.get("profile_diff", {}) if isinstance(diff_audit.get("profile_diff"), dict) else {}

            artifact_set = bundle_diff.get("artifact_set", {}) if isinstance(bundle_diff.get("artifact_set"), dict) else {}
            profile_set = profile_diff.get("profile_set", {}) if isinstance(profile_diff.get("profile_set"), dict) else {}

            delta_summary["bundle_added"] = [str(x) for x in artifact_set.get("added", [])] if isinstance(artifact_set.get("added"), list) else []
            delta_summary["bundle_removed"] = [str(x) for x in artifact_set.get("removed", [])] if isinstance(artifact_set.get("removed"), list) else []
            delta_summary["bundle_sha_changed"] = [str(x) for x in bundle_diff.get("sha256_changed", [])] if isinstance(bundle_diff.get("sha256_changed"), list) else []

            delta_summary["profile_added"] = [str(x) for x in profile_set.get("added", [])] if isinstance(profile_set.get("added"), list) else []
            delta_summary["profile_removed"] = [str(x) for x in profile_set.get("removed", [])] if isinstance(profile_set.get("removed"), list) else []

            delta_summary["profile_selected_added"] = _flatten_profile_deltas(profile_diff, "selected_added")
            delta_summary["profile_selected_removed"] = _flatten_profile_deltas(profile_diff, "selected_removed")
            delta_summary["profile_sha_changed"] = _flatten_profile_deltas(profile_diff, "sha_changed")

            has_any_diff = any(bool(v) for v in delta_summary.values())
            has_removal = bool(delta_summary["bundle_removed"] or delta_summary["profile_removed"] or delta_summary["profile_selected_removed"])
            has_sha_change = bool(delta_summary["bundle_sha_changed"] or delta_summary["profile_sha_changed"])
            has_profile_set_add = bool(delta_summary["profile_added"])

            added_paths = sorted(set(delta_summary["bundle_added"] + delta_summary["profile_selected_added"]))
            only_allowed_additions = _all_match_allowed(added_paths, policy_patterns) if added_paths else True

            if not has_any_diff:
                decision = DECISION_ALLOW
                decision_reasons.append("no_diff_detected")
            elif has_removal:
                decision = DECISION_REJECT
                decision_reasons.append("removal_detected")
            elif has_sha_change or has_profile_set_add:
                decision = DECISION_HUMAN_APPROVAL_REQUIRED
                if has_sha_change:
                    decision_reasons.append("sha_change_detected")
                if has_profile_set_add:
                    decision_reasons.append("profile_set_change_detected")
            elif only_allowed_additions:
                decision = DECISION_ALLOW
                decision_reasons.append("allowed_additions_only")
            else:
                decision = DECISION_HUMAN_APPROVAL_REQUIRED
                decision_reasons.append("non_allowlisted_additions_detected")
                warnings.append("one or more additions are outside allowlist patterns")

    report = {
        "schema_version": IR25_SCHEMA_VERSION,
        "phase": "IR25",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "decision": decision,
        "decision_reasons": decision_reasons,
        "validation_failed_checks": failed_checks,
        "validation_warnings": warnings,
        "policy": {
            "allowed_addition_patterns": policy_patterns,
        },
        "delta_summary": delta_summary,
        "summary": {
            "decision": decision,
            "reason_count": len(decision_reasons),
            "failed_check_count": len(failed_checks),
            "warning_count": len(warnings),
            "bundle_added_count": len(delta_summary["bundle_added"]),
            "bundle_removed_count": len(delta_summary["bundle_removed"]),
            "bundle_sha_changed_count": len(delta_summary["bundle_sha_changed"]),
            "profile_added_count": len(delta_summary["profile_added"]),
            "profile_removed_count": len(delta_summary["profile_removed"]),
            "profile_selected_added_count": len(delta_summary["profile_selected_added"]),
            "profile_selected_removed_count": len(delta_summary["profile_selected_removed"]),
            "profile_sha_changed_count": len(delta_summary["profile_sha_changed"]),
        },
        "artifacts": {
            "ir24_diff_report": str(diff_path.relative_to(project_root).as_posix()) if diff_path.exists() and str(diff_path).startswith(str(project_root)) else str(diff_path),
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir25_submission_change_approval_gate_report_{_safe(source_task_id)}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "gate_report": report,
        "external_write_executed": False,
    }


def write_ir25_completion_report(
    *,
    base_path: Path,
    ir25_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR25-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    gate = ir25_output.get("gate_report", {}) if isinstance(ir25_output, dict) else {}

    completion = {
        "phase": "Implementation Restart Phase 25",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR25_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "decision": gate.get("decision", "UNKNOWN"),
        "validation_failed_check_count": len(gate.get("validation_failed_checks", [])),
        "validation_warning_count": len(gate.get("validation_warnings", [])),
        "summary": gate.get("summary", {}),
        "artifacts": {
            "gate_report": ir25_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase25_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "execution_policy_execute": False,
            "external_write_executed": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase25_completion_report.json"
    out_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": completion,
        "external_write_executed": False,
    }

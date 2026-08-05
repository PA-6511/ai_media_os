"""
core_ai_receiver_dryrun.py - IR11

Validate IR10 phase decision package as a Core AI receiver dry-run.
No external I/O beyond local report files.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .connection_dryrun_validator import validate_connection_dryrun

IR10_SCHEMA_VERSION = "ir10_core_phase_decision_v1"
IR11_SCHEMA_VERSION = "ir11_core_receiver_v1"

_EXPECTED_MAPPING: dict[str, dict[str, str]] = {
    "PASS": {
        "recommended_decision": "RECOMMEND_APPROVE_DRY_RUN_ONLY",
        "core_receive_rule": "ACCEPT_DRY_RUN_REVIEW_QUEUE",
    },
    "WARN": {
        "recommended_decision": "REQUIRE_HUMAN_REVIEW",
        "core_receive_rule": "HUMAN_REVIEW_REQUIRED",
    },
    "FAIL": {
        "recommended_decision": "RECOMMEND_REJECT",
        "core_receive_rule": "REJECT_AND_KEEP_NO_GO",
    },
    "ABORT": {
        "recommended_decision": "BLOCKED_BY_POLICY",
        "core_receive_rule": "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE",
    },
}


@dataclass
class ReceiverValidationResult:
    result: str  # PASS | WARN | FAIL
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_judgment(value: Any) -> str:
    text = str(value or "WARN").upper()
    return text if text in _EXPECTED_MAPPING else "WARN"


def _validate_warn_human_review_package(
    package: dict[str, Any] | None,
    *,
    source_task_id: str,
) -> ReceiverValidationResult:
    failed: list[str] = []
    warnings: list[str] = []

    if not isinstance(package, dict):
        failed.append("warn human_review package is required")
        return ReceiverValidationResult(result="FAIL", failed_checks=failed, warnings=warnings)

    if package.get("schema_version") != IR10_SCHEMA_VERSION:
        failed.append(f"human_review.schema_version must be {IR10_SCHEMA_VERSION}")
    if package.get("status") != "PENDING_HUMAN_REVIEW":
        failed.append("human_review.status must be PENDING_HUMAN_REVIEW")

    required_actions = package.get("required_actions", [])
    if "review_warn_candidates" not in required_actions:
        failed.append("human_review.required_actions must include review_warn_candidates")
    if "approve_or_reject_decision_package" not in required_actions:
        failed.append("human_review.required_actions must include approve_or_reject_decision_package")

    if package.get("source_task_id") not in {source_task_id, f"{source_task_id}_ir10"}:
        warnings.append("human_review.source_task_id does not match source_task_id")

    safeguards = package.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("human_review.safeguards.external_write_executed must be false")

    return ReceiverValidationResult(
        result="FAIL" if failed else ("WARN" if warnings else "PASS"),
        failed_checks=failed,
        warnings=warnings,
    )


def _validate_abort_evidence_bundle(
    bundle: dict[str, Any] | None,
    *,
    source_task_id: str,
) -> ReceiverValidationResult:
    failed: list[str] = []
    warnings: list[str] = []

    if not isinstance(bundle, dict):
        failed.append("abort evidence bundle is required")
        return ReceiverValidationResult(result="FAIL", failed_checks=failed, warnings=warnings)

    if bundle.get("schema_version") != IR10_SCHEMA_VERSION:
        failed.append(f"abort_bundle.schema_version must be {IR10_SCHEMA_VERSION}")
    if bundle.get("status") != "ABORT_LOCKED":
        failed.append("abort_bundle.status must be ABORT_LOCKED")

    evidence_lock = bundle.get("evidence_lock", {})
    if evidence_lock.get("required") is not True:
        failed.append("abort_bundle.evidence_lock.required must be true")
    if evidence_lock.get("allow_delete") is not False:
        failed.append("abort_bundle.evidence_lock.allow_delete must be false")
    if evidence_lock.get("allow_overwrite") is not False:
        failed.append("abort_bundle.evidence_lock.allow_overwrite must be false")

    must_preserve = set(bundle.get("audit_must_preserve", []))
    for required in ["roundtrip_output", "quality_gate_items", "core_phase_decision_package"]:
        if required not in must_preserve:
            failed.append(f"abort_bundle.audit_must_preserve must include {required}")

    if bundle.get("source_task_id") not in {source_task_id, f"{source_task_id}_ir10"}:
        warnings.append("abort_bundle.source_task_id does not match source_task_id")

    safeguards = bundle.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("abort_bundle.safeguards.external_write_executed must be false")

    return ReceiverValidationResult(
        result="FAIL" if failed else ("WARN" if warnings else "PASS"),
        failed_checks=failed,
        warnings=warnings,
    )


def validate_ir10_phase_decision_package_for_core(
    *,
    phase_decision_package: dict[str, Any],
    source_task_id: str,
) -> ReceiverValidationResult:
    """
    IR11-T1/T2
    Validate IR10 phase decision package for Core receiver acceptance.
    """
    failed: list[str] = []
    warnings: list[str] = []

    if phase_decision_package.get("schema_version") != IR10_SCHEMA_VERSION:
        failed.append(f"schema_version must be {IR10_SCHEMA_VERSION}")

    judgment = _normalize_judgment(phase_decision_package.get("quality_gate_judgment"))
    expected = _EXPECTED_MAPPING[judgment]
    mapping_rule = phase_decision_package.get("mapping_rule", {})

    if mapping_rule.get("recommended_decision") != expected["recommended_decision"]:
        failed.append(
            "mapping_rule.recommended_decision does not match judgment"
        )
    if mapping_rule.get("core_receive_rule") != expected["core_receive_rule"]:
        failed.append(
            "mapping_rule.core_receive_rule does not match judgment"
        )

    handshake_package = phase_decision_package.get("core_phase_decision_package")
    if not isinstance(handshake_package, dict):
        failed.append("core_phase_decision_package is required")
    else:
        handshake_validation = validate_connection_dryrun(handshake_package)
        if handshake_validation.result == "FAIL":
            failed.extend(
                [f"handshake:{item}" for item in handshake_validation.failed_checks]
            )
        else:
            warnings.extend(
                [f"handshake:{item}" for item in handshake_validation.warnings]
            )

        decision = handshake_package.get("decision_package", {})
        if decision.get("recommended_decision") != expected["recommended_decision"]:
            failed.append("handshake decision_package.recommended_decision mismatch")

    meta = handshake_package.get("_meta", {}) if isinstance(handshake_package, dict) else {}
    handshake_source_task = str(meta.get("source_task_id", ""))
    if source_task_id not in handshake_source_task:
        warnings.append("handshake _meta.source_task_id does not include source_task_id")

    return ReceiverValidationResult(
        result="FAIL" if failed else ("WARN" if warnings else "PASS"),
        failed_checks=failed,
        warnings=warnings,
    )


def run_ir11_core_receiver_dryrun(
    *,
    base_path: Path,
    source_task_id: str,
    phase_decision_package: dict[str, Any],
    human_review_package: dict[str, Any] | None = None,
    abort_evidence_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    IR11-T1/T2/T3/T4
    Validate Core-side receive rules for IR10 outputs in dry-run mode.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    main_validation = validate_ir10_phase_decision_package_for_core(
        phase_decision_package=phase_decision_package,
        source_task_id=source_task_id,
    )

    judgment = _normalize_judgment(phase_decision_package.get("quality_gate_judgment"))

    warn_validation = ReceiverValidationResult(result="PASS")
    abort_validation = ReceiverValidationResult(result="PASS")

    if judgment == "WARN":
        warn_validation = _validate_warn_human_review_package(
            human_review_package,
            source_task_id=source_task_id,
        )
    if judgment == "ABORT":
        abort_validation = _validate_abort_evidence_bundle(
            abort_evidence_bundle,
            source_task_id=source_task_id,
        )

    all_failed = [
        *main_validation.failed_checks,
        *warn_validation.failed_checks,
        *abort_validation.failed_checks,
    ]
    all_warnings = [
        *main_validation.warnings,
        *warn_validation.warnings,
        *abort_validation.warnings,
    ]

    overall = "FAIL" if all_failed else ("WARN" if all_warnings else "PASS")

    receiver_report = {
        "schema_version": IR11_SCHEMA_VERSION,
        "phase": "IR11",
        "generated_at": _now_iso(),
        "source_task_id": source_task_id,
        "quality_gate_judgment": judgment,
        "core_receive_rule": phase_decision_package.get("mapping_rule", {}).get("core_receive_rule"),
        "validation_result": overall,
        "validation_failed_checks": all_failed,
        "validation_warnings": all_warnings,
        "sub_validations": {
            "phase_decision_package": {
                "result": main_validation.result,
                "failed_checks": main_validation.failed_checks,
                "warnings": main_validation.warnings,
            },
            "warn_human_review_package": {
                "result": warn_validation.result,
                "failed_checks": warn_validation.failed_checks,
                "warnings": warn_validation.warnings,
            },
            "abort_evidence_bundle": {
                "result": abort_validation.result,
                "failed_checks": abort_validation.failed_checks,
                "warnings": abort_validation.warnings,
            },
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / f"ir11_core_receiver_dryrun_{source_task_id}.json"
    out_path.write_text(json.dumps(receiver_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "receiver_report": receiver_report,
        "external_write_executed": False,
    }


def write_ir11_completion_report(
    *,
    base_path: Path,
    ir11_output: dict[str, Any],
    focused_tests: dict[str, int] | None = None,
    full_regression: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    IR11-T5 completion report.
    """
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    focused = focused_tests or {"passed": 0, "failed": 0}
    regression = full_regression or {"passed": 0, "failed": 0}

    receiver_report = ir11_output.get("receiver_report", {}) if isinstance(ir11_output, dict) else {}

    report = {
        "phase": "Implementation Restart Phase 11",
        "status": "COMPLETED",
        "generated_at": _now_iso(),
        "schema_version": IR11_SCHEMA_VERSION,
        "test_result": {
            "focused_tests": focused,
            "full_regression": regression,
        },
        "quality_gate_judgment": receiver_report.get("quality_gate_judgment", "UNKNOWN"),
        "core_receive_rule": receiver_report.get("core_receive_rule", "UNKNOWN"),
        "validation_result": receiver_report.get("validation_result", "UNKNOWN"),
        "artifacts": {
            "ir11_receiver_report": ir11_output.get("path", "UNKNOWN"),
            "completion_report": "reports/implementation_restart_phase11_completion_report.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }

    out_path = reports_dir / "implementation_restart_phase11_completion_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(out_path),
        "completion_report": report,
        "external_write_executed": False,
    }

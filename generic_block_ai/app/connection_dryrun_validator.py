"""
connection_dryrun_validator.py — IR4-T3

core_ai_handshake_package の安全制約を検証します。
外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core_ai_handshake_package import REQUIRED_SAFETY_GATES, HANDSHAKE_SCHEMA_VERSION


@dataclass
class ConnectionValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


VALID_CONNECTION_STATUSES = {
    "HANDSHAKE_READY_DRY_RUN",
    "HANDSHAKE_PENDING_REVIEW",
    "HANDSHAKE_REJECTED",
    "HANDSHAKE_BLOCKED",
}


def validate_connection_dryrun(data: dict[str, Any]) -> ConnectionValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    meta = data.get("_meta", {})
    contract = data.get("handshake_contract", {})
    safeguards = data.get("safeguards", {})
    expectations = data.get("validation_expectations", {})
    decision_package = data.get("decision_package", {})
    connection_status = data.get("connection_status", "")

    # schema version
    if meta.get("schema_version") != HANDSHAKE_SCHEMA_VERSION:
        failed.append(f"_meta.schema_version must be {HANDSHAKE_SCHEMA_VERSION}")

    # handshake_contract — all required safety gates
    for key, expected in REQUIRED_SAFETY_GATES.items():
        if contract.get(key) != expected:
            failed.append(f"handshake_contract.{key} must be {expected!r}")

    # safeguards — all false/true invariants
    if safeguards.get("actual_auto_approve") is not False:
        failed.append("safeguards.actual_auto_approve must be false")
    if safeguards.get("actual_auto_execute") is not False:
        failed.append("safeguards.actual_auto_execute must be false")
    if safeguards.get("external_write_executed") is not False:
        failed.append("safeguards.external_write_executed must be false")
    if safeguards.get("production_release") is not False:
        failed.append("safeguards.production_release must be false")
    if safeguards.get("requires_human_signoff") is not True:
        failed.append("safeguards.requires_human_signoff must be true")

    # validation_expectations
    if expectations.get("must_not_trigger_execution") is not True:
        failed.append("validation_expectations.must_not_trigger_execution must be true")
    if expectations.get("must_not_create_external_request") is not True:
        failed.append("validation_expectations.must_not_create_external_request must be true")
    if expectations.get("must_not_change_runtime_mode") is not True:
        failed.append("validation_expectations.must_not_change_runtime_mode must be true")
    if expectations.get("must_preserve_no_go_status") is not True:
        failed.append("validation_expectations.must_preserve_no_go_status must be true")
    if expectations.get("core_ai_expected_behavior") != "observe_and_return_assessment_only":
        failed.append(
            "validation_expectations.core_ai_expected_behavior must be observe_and_return_assessment_only"
        )

    # connection_status
    if connection_status not in VALID_CONNECTION_STATUSES:
        failed.append(f"connection_status must be one of {sorted(VALID_CONNECTION_STATUSES)}")

    # decision_package presence
    if not decision_package.get("recommended_decision"):
        failed.append("decision_package.recommended_decision is required")
    if decision_package.get("policy_hash") is None:
        warns.append("decision_package.policy_hash is not set")
    if decision_package.get("quality_score") is None:
        warns.append("decision_package.quality_score is not set")

    if failed:
        return ConnectionValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ConnectionValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ConnectionValidationResult(result="PASS")

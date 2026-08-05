"""
handoff_payload_validator.py  –  Phase 4-4

Phase 4 の decision package handoff payload JSON をローカル検証します。
外部通信・自動実行・export は一切行いません。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_BLOCKED_ACTIONS = {
    "external_api_call",
    "wordpress_operation",
    "cron_registration",
    "auto_execute",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "production_execution",
}


@dataclass
class ValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_handoff_payload(data: dict[str, Any]) -> ValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    contract = data.get("handoff_contract", {})
    source = data.get("source", {})
    target = data.get("target", {})
    payload = data.get("payload", {})
    expectations = data.get("validation_expectations", {})

    if contract.get("connection_test_mode") is not True:
        failed.append("handoff_contract.connection_test_mode must be true")

    if contract.get("connection_scope") != "decision_package_handoff_only":
        failed.append("handoff_contract.connection_scope must be decision_package_handoff_only")

    if contract.get("operation_mode") != "OBSERVE":
        failed.append("handoff_contract.operation_mode must be OBSERVE")

    if contract.get("execution") != "dry_run":
        failed.append("handoff_contract.execution must be dry_run")

    if contract.get("requires_human_approval") is not True:
        failed.append("handoff_contract.requires_human_approval must be true")

    if contract.get("auto_execute_allowed") is not False:
        failed.append("handoff_contract.auto_execute_allowed must be false")

    if contract.get("transport") != "none":
        failed.append("handoff_contract.transport must be none")

    if contract.get("external_api_call") is not False:
        failed.append("handoff_contract.external_api_call must be false")

    if source.get("artifact_type") != "decision_package":
        failed.append("source.artifact_type must be decision_package")

    if source.get("artifact_path") != "reports/phase35_decision_package.json":
        failed.append("source.artifact_path must reference reports/phase35_decision_package.json")

    if target.get("mode") != "observation_only":
        failed.append("target.mode must be observation_only")

    if target.get("execution_permission") != "none":
        failed.append("target.execution_permission must be none")

    if target.get("write_permission") != "none":
        failed.append("target.write_permission must be none")

    if payload.get("decision_package_ref") != "reports/phase35_decision_package.json":
        failed.append("payload.decision_package_ref must reference reports/phase35_decision_package.json")

    if payload.get("required_review_state") != "HUMAN_REVIEW_REQUIRED":
        failed.append("payload.required_review_state must be HUMAN_REVIEW_REQUIRED")

    if payload.get("expected_core_ai_behavior") != "observe_and_return_assessment_only":
        failed.append("payload.expected_core_ai_behavior must be observe_and_return_assessment_only")

    blocked_actions = set(payload.get("blocked_actions", []))
    missing_blocked = REQUIRED_BLOCKED_ACTIONS - blocked_actions
    if missing_blocked:
        failed.append(f"payload.blocked_actions is missing required entries: {sorted(missing_blocked)}")

    if expectations.get("must_not_trigger_execution") is not True:
        failed.append("validation_expectations.must_not_trigger_execution must be true")

    if expectations.get("must_not_create_external_request") is not True:
        failed.append("validation_expectations.must_not_create_external_request must be true")

    if expectations.get("must_not_change_runtime_mode") is not True:
        failed.append("validation_expectations.must_not_change_runtime_mode must be true")

    if expectations.get("must_preserve_no_go_status") is not True:
        failed.append("validation_expectations.must_preserve_no_go_status must be true")

    if data.get("result") != "PASS_DRY_RUN_ONLY":
        warns.append("result should remain PASS_DRY_RUN_ONLY")

    if failed:
        return ValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ValidationResult(result="PASS")

"""
connection_test_result_validator.py  –  Phase 4-5

Phase 4 の limited connection test report JSON をローカル検証します。
外部通信・自動実行・export は一切行いません。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_ALLOWED_STATES = {"OBSERVE", "DRY_RUN", "HUMAN_REVIEW_REQUIRED"}
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


def validate_connection_test_result(data: dict[str, Any]) -> ValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    scope = data.get("scope", {})
    judgment = data.get("judgment", {})
    blocked_actions = set(data.get("blocked_actions", []))
    referenced_artifacts = data.get("referenced_artifacts", [])
    verified_items = data.get("verified_items", [])
    unverified_items = data.get("unverified_items", [])

    if scope.get("connection_test_mode") is not True:
        failed.append("scope.connection_test_mode must be true")

    if scope.get("connection_scope") != "decision_package_handoff_only":
        failed.append("scope.connection_scope must be decision_package_handoff_only")

    if scope.get("operation_mode") != "OBSERVE":
        failed.append("scope.operation_mode must be OBSERVE")

    if scope.get("execution") != "dry_run":
        failed.append("scope.execution must be dry_run")

    if judgment.get("connection_test_status") != "PASS_DRY_RUN_ONLY":
        failed.append("judgment.connection_test_status must be PASS_DRY_RUN_ONLY")

    if judgment.get("production_status") != "NO_GO":
        failed.append("judgment.production_status must be NO_GO")

    allowed_state = set(judgment.get("allowed_state", []))
    missing_states = REQUIRED_ALLOWED_STATES - allowed_state
    if missing_states:
        failed.append(f"judgment.allowed_state is missing required entries: {sorted(missing_states)}")

    if judgment.get("dangerous_operations_detected") is not False:
        failed.append("judgment.dangerous_operations_detected must be false")

    if judgment.get("external_communication") is not False:
        failed.append("judgment.external_communication must be false")

    if judgment.get("auto_execution") is not False:
        failed.append("judgment.auto_execution must be false")

    missing_blocked = REQUIRED_BLOCKED_ACTIONS - blocked_actions
    if missing_blocked:
        failed.append(f"blocked_actions is missing required entries: {sorted(missing_blocked)}")

    if len(referenced_artifacts) < 2:
        failed.append("referenced_artifacts must include at least phase4_1 and phase4_2 artifacts")

    if not verified_items:
        failed.append("verified_items must not be empty")

    if not unverified_items:
        warns.append("unverified_items should document remaining non-tested areas")

    if failed:
        return ValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ValidationResult(result="PASS")

"""
review_queue_validator.py  –  Phase 3.5-15

review queue JSON の安全制約を検証します。
外部通信・自動 dequeue・実行は一切行いません。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_FORBIDDEN_ACTIONS = {
    "auto_dequeue",
    "auto_execute",
    "auto_publish",
    "batch_approve_without_review",
}


@dataclass
class ValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_review_queue(data: dict[str, Any]) -> ValidationResult:
    """
    review queue dict を検証し ValidationResult を返す。
    外部 I/O・自動処理・auto_approve は行わない。
    """
    failed: list[str] = []
    warns: list[str] = []

    meta = data.get("queue_metadata", {})
    policy = data.get("queue_policy", {})

    # --- REJECT conditions ---
    if meta.get("mode") != "dry_run":
        failed.append("queue_metadata.mode must be dry_run")

    if meta.get("operation_mode") != "OBSERVE":
        failed.append("queue_metadata.operation_mode must be OBSERVE")

    if meta.get("auto_process_allowed") is not False:
        failed.append("queue_metadata.auto_process_allowed must be false")

    if meta.get("requires_human_approval") is not True:
        failed.append("queue_metadata.requires_human_approval must be true")

    if policy.get("auto_approve") is not False:
        failed.append("queue_policy.auto_approve must be false")

    if meta.get("mode") in {"live", "production", "execute"}:
        failed.append(f"queue_metadata.mode '{meta.get('mode')}' is forbidden")

    if meta.get("operation_mode") in {"EXECUTE", "WRITE", "PUBLISH"}:
        failed.append(f"queue_metadata.operation_mode '{meta.get('operation_mode')}' is forbidden")

    # --- WARN conditions ---
    if policy.get("escalation_enabled"):
        warns.append("queue_policy.escalation_enabled is true — escalation outside approval flow is discouraged")

    forbidden_actions = set(policy.get("forbidden_auto_actions", []))
    missing = REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions
    if missing:
        warns.append(f"queue_policy.forbidden_auto_actions is missing required entries: {sorted(missing)}")

    if failed:
        return ValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ValidationResult(result="PASS")

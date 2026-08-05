"""
proposal_validator.py  –  Phase 3.5-14

proposal package JSON の安全制約を検証します。
外部通信・自動実行・export は一切行いません。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_proposal(data: dict[str, Any]) -> ValidationResult:
    """
    proposal package dict を検証し ValidationResult を返す。
    外部 I/O・実行・自動 approve は行わない。
    """
    failed: list[str] = []
    warns: list[str] = []

    proposal = data.get("proposal", {})
    constraints = data.get("safety_constraints", {})
    review_req = data.get("review_requirements", {})
    impact = proposal.get("estimated_impact", {})

    # --- REJECT conditions ---
    if proposal.get("mode") != "dry_run":
        failed.append("proposal.mode must be dry_run")

    if proposal.get("operation_mode") != "OBSERVE":
        failed.append("proposal.operation_mode must be OBSERVE")

    if impact.get("auto_execute_allowed") is not False:
        failed.append("estimated_impact.auto_execute_allowed must be false")

    if impact.get("requires_human_approval") is not True:
        failed.append("estimated_impact.requires_human_approval must be true")

    if constraints.get("publish_content") is not False:
        failed.append("safety_constraints.publish_content must be false")

    if constraints.get("delete_data") is not False:
        failed.append("safety_constraints.delete_data must be false")

    if constraints.get("change_config") is not False:
        failed.append("safety_constraints.change_config must be false")

    if constraints.get("observe_only") is not True:
        failed.append("safety_constraints.observe_only must be true")

    if review_req.get("requires_human_approval") is not True:
        failed.append("review_requirements.requires_human_approval must be true")

    # --- forbidden values ---
    forbidden_modes = {"live", "production", "execute"}
    if proposal.get("mode") in forbidden_modes:
        failed.append(f"proposal.mode '{proposal.get('mode')}' is forbidden")

    forbidden_ops = {"EXECUTE", "WRITE", "PUBLISH"}
    if proposal.get("operation_mode") in forbidden_ops:
        failed.append(f"proposal.operation_mode '{proposal.get('operation_mode')}' is forbidden")

    status = data.get("status", {})
    if status.get("reviewer_decision") == "auto_approved":
        failed.append("status.reviewer_decision 'auto_approved' is forbidden")

    # --- WARN conditions ---
    if not constraints.get("forbidden_actions_checked"):
        warns.append("safety_constraints.forbidden_actions_checked is not set")

    if failed:
        return ValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ValidationResult(result="PASS")

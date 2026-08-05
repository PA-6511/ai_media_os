from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .block_contract import BlockManifest


@dataclass(frozen=True)
class GuardDecision:
    allowed_actions: list[dict[str, Any]]
    blocked_actions: list[dict[str, Any]]
    needs_review_actions: list[dict[str, Any]]
    reason_codes: list[dict[str, str]]
    warnings: list[str]


def validate_runtime_configuration(manifest: BlockManifest, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if manifest.operation_mode != "OBSERVE":
        errors.append("operation_mode must be OBSERVE")

    if policy.get("observe_only") is not True:
        errors.append("policy.observe_only must be true")

    if manifest.mode != "dry_run":
        errors.append("manifest.mode must remain dry_run")

    if not manifest.requires_human_approval:
        errors.append("requires_human_approval must remain true")

    if manifest.auto_execute_allowed:
        errors.append("auto_execute_allowed must remain false")

    dangerous_capabilities = ("publish_content", "delete_data", "change_config")
    for capability_name in dangerous_capabilities:
        if manifest.capabilities.get(capability_name, False):
            errors.append(f"capability must remain disabled: {capability_name}")

    return errors


def load_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy root must be an object")
    return payload


def evaluate_actions(
    manifest: BlockManifest,
    requested_actions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> GuardDecision:
    forbidden = set(manifest.forbidden_actions)
    forbidden.update(str(item) for item in policy.get("forbidden_actions", []))

    allowed: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    reason_codes: list[dict[str, str]] = []
    warnings: list[str] = []

    enabled_capabilities = {name for name, enabled in manifest.capabilities.items() if enabled}

    for action in requested_actions:
        action_type = str(action.get("type", "")).strip()
        if not action_type:
            blocked.append(action)
            reason_codes.append({"action_type": "", "classification": "block", "reason": "missing_action_type"})
            warnings.append("action without type was blocked")
            continue

        if action_type in forbidden:
            blocked.append(action)
            reason_codes.append(
                {
                    "action_type": action_type,
                    "classification": "block",
                    "reason": "forbidden_action",
                }
            )
            warnings.append(f"forbidden action blocked: {action_type}")
            continue

        if action_type == "publish_content" and not manifest.capabilities.get("publish_content", False):
            blocked.append(action)
            reason_codes.append(
                {
                    "action_type": action_type,
                    "classification": "block",
                    "reason": "capability_disabled",
                }
            )
            warnings.append("publish_content is disabled by manifest capabilities")
            continue

        if action_type == "delete_data" and not manifest.capabilities.get("delete_data", False):
            blocked.append(action)
            reason_codes.append(
                {
                    "action_type": action_type,
                    "classification": "block",
                    "reason": "capability_disabled",
                }
            )
            warnings.append("delete_data is disabled by manifest capabilities")
            continue

        if action_type == "change_config" and not manifest.capabilities.get("change_config", False):
            blocked.append(action)
            reason_codes.append(
                {
                    "action_type": action_type,
                    "classification": "block",
                    "reason": "capability_disabled",
                }
            )
            warnings.append("change_config is disabled by manifest capabilities")
            continue

        if action_type not in enabled_capabilities:
            needs_review.append(action)
            reason_codes.append(
                {
                    "action_type": action_type,
                    "classification": "needs_review",
                    "reason": "unknown_action_type",
                }
            )
            warnings.append(f"action requires review: {action_type}")
            continue

        allowed.append(action)
        reason_codes.append(
            {
                "action_type": action_type,
                "classification": "allow",
                "reason": "capability_enabled",
            }
        )

    return GuardDecision(
        allowed_actions=allowed,
        blocked_actions=blocked,
        needs_review_actions=needs_review,
        reason_codes=reason_codes,
        warnings=warnings,
    )

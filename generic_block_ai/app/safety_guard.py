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
    warnings: list[str]


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
    warnings: list[str] = []

    for action in requested_actions:
        action_type = str(action.get("type", "")).strip()
        if not action_type:
            blocked.append(action)
            warnings.append("action without type was blocked")
            continue

        if action_type in forbidden:
            blocked.append(action)
            warnings.append(f"forbidden action blocked: {action_type}")
            continue

        if action_type == "publish_content" and not manifest.capabilities.get("publish_content", False):
            blocked.append(action)
            warnings.append("publish_content is disabled by manifest capabilities")
            continue

        if action_type == "delete_data" and not manifest.capabilities.get("delete_data", False):
            blocked.append(action)
            warnings.append("delete_data is disabled by manifest capabilities")
            continue

        if action_type == "change_config" and not manifest.capabilities.get("change_config", False):
            blocked.append(action)
            warnings.append("change_config is disabled by manifest capabilities")
            continue

        allowed.append(action)

    return GuardDecision(allowed_actions=allowed, blocked_actions=blocked, warnings=warnings)

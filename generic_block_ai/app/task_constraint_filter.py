from __future__ import annotations

from typing import Any

from .block_contract import BlockManifest


LOW_PRIORITY_THRESHOLD = 40
HIGH_RISK_THRESHOLD = 80


def filter_task_candidates(
    candidates: list[dict[str, Any]],
    *,
    manifest: BlockManifest,
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    forbidden = set(manifest.forbidden_actions)
    forbidden.update(str(item).strip() for item in policy.get("forbidden_actions", []))

    for candidate in candidates:
        action = candidate.get("action", {})
        action_type = str(candidate.get("action_type", "")).strip()
        target = str(action.get("target", "")).strip()
        rejection_reasons: list[dict[str, str]] = []

        if action_type in forbidden:
            rejection_reasons.append(
                {
                    "code": "forbidden_action",
                    "message": f"action type is forbidden: {action_type}",
                }
            )

        if action_type in manifest.capabilities and not manifest.capabilities.get(action_type, False):
            rejection_reasons.append(
                {
                    "code": "capability_mismatch",
                    "message": f"capability is disabled for action type: {action_type}",
                }
            )

        if not target:
            rejection_reasons.append(
                {
                    "code": "missing_mandatory_context",
                    "message": "action.target is required",
                }
            )

        if int(candidate.get("risk_score", 0)) >= HIGH_RISK_THRESHOLD and int(
            candidate.get("priority_score", 0)
        ) < LOW_PRIORITY_THRESHOLD:
            rejection_reasons.append(
                {
                    "code": "high_risk_low_priority",
                    "message": "candidate is high-risk and low-priority",
                }
            )

        if rejection_reasons:
            rejected_candidate = dict(candidate)
            rejected_candidate["rejection_reasons"] = rejection_reasons
            rejected.append(rejected_candidate)
            continue

        accepted.append(candidate)

    return accepted, rejected
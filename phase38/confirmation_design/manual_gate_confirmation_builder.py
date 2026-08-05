"""Phase38: manual gate confirmation builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_confirmation(confirmation_package: dict[str, Any]) -> dict[str, Any]:
    if confirmation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_confirmation_package"}
    return {
        "status": "MANUAL_GATE_CONFIRMATION_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE39_PLANNING_ONLY", "REJECT"],
    }

"""Phase39: manual gate authorization builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_authorization(authorization_package: dict[str, Any]) -> dict[str, Any]:
    if authorization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_authorization_package"}
    return {
        "status": "MANUAL_GATE_AUTHORIZATION_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE40_PLANNING_ONLY", "REJECT"],
    }

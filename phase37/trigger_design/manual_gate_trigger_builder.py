"""Phase37: manual gate trigger builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_trigger(trigger_package: dict[str, Any]) -> dict[str, Any]:
    if trigger_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_trigger_package"}
    return {
        "status": "MANUAL_GATE_TRIGGER_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE38_PLANNING_ONLY", "REJECT"],
    }

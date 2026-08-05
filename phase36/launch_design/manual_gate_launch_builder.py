"""Phase36: manual gate launch builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_launch(launch_package: dict[str, Any]) -> dict[str, Any]:
    if launch_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_launch_package"}
    return {
        "status": "MANUAL_GATE_LAUNCH_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE37_PLANNING_ONLY", "REJECT"],
    }

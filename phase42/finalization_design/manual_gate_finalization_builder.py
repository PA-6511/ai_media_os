"""Phase42: manual gate finalization builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_finalization(finalization_package: dict[str, Any]) -> dict[str, Any]:
    if finalization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_finalization_package"}
    return {
        "status": "MANUAL_GATE_FINALIZATION_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE43_PLANNING_ONLY", "REJECT"],
    }

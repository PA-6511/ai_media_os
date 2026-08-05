"""Phase40: manual gate validation builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_validation(validation_package: dict[str, Any]) -> dict[str, Any]:
    if validation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_validation_package"}
    return {
        "status": "MANUAL_GATE_VALIDATION_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE41_PLANNING_ONLY", "REJECT"],
    }

"""Phase41: manual gate certification builder."""
from __future__ import annotations

from typing import Any


def build_manual_gate_certification(certification_package: dict[str, Any]) -> dict[str, Any]:
    if certification_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_certification_package"}
    return {
        "status": "MANUAL_GATE_CERTIFICATION_READY",
        "approval_required": True,
        "allow_does_not_execute": True,
        "allowed_decisions": ["ALLOW_PHASE42_PLANNING_ONLY", "REJECT"],
    }

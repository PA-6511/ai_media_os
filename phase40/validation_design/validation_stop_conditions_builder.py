"""Phase40: validation stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_validation_stop_conditions(validation_package: dict[str, Any]) -> dict[str, Any]:
    if validation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_validation_package"}
    return {
        "status": "VALIDATION_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "validation_stop_conditions_does_not_execute": True,
    }

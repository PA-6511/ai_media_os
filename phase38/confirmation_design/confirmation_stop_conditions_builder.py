"""Phase38: confirmation stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_confirmation_stop_conditions(confirmation_package: dict[str, Any]) -> dict[str, Any]:
    if confirmation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_confirmation_package"}
    return {
        "status": "CONFIRMATION_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "confirmation_stop_conditions_does_not_execute": True,
    }

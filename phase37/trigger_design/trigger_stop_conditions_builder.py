"""Phase37: trigger stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_trigger_stop_conditions(trigger_package: dict[str, Any]) -> dict[str, Any]:
    if trigger_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_trigger_package"}
    return {
        "status": "TRIGGER_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "trigger_stop_conditions_does_not_execute": True,
    }

"""Phase37: trigger controls builder."""
from __future__ import annotations

from typing import Any


def build_trigger_controls(trigger_package: dict[str, Any]) -> dict[str, Any]:
    if trigger_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_trigger_package"}
    return {
        "status": "TRIGGER_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "trigger_controls_does_not_execute": True,
    }

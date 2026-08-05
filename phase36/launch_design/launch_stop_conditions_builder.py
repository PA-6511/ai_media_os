"""Phase36: launch stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_launch_stop_conditions(launch_package: dict[str, Any]) -> dict[str, Any]:
    if launch_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_launch_package"}
    return {
        "status": "LAUNCH_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "launch_stop_conditions_does_not_execute": True,
    }

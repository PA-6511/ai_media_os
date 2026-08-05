"""Phase36: launch controls builder."""
from __future__ import annotations

from typing import Any


def build_launch_controls(launch_package: dict[str, Any]) -> dict[str, Any]:
    if launch_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_launch_package"}
    return {
        "status": "LAUNCH_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "launch_controls_does_not_execute": True,
    }

"""Phase42: finalization controls builder."""
from __future__ import annotations

from typing import Any


def build_finalization_controls(finalization_package: dict[str, Any]) -> dict[str, Any]:
    if finalization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_finalization_package"}
    return {
        "status": "FINALIZATION_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "finalization_controls_does_not_execute": True,
    }

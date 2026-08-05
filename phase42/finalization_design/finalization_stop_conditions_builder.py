"""Phase42: finalization stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_finalization_stop_conditions(finalization_package: dict[str, Any]) -> dict[str, Any]:
    if finalization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_finalization_package"}
    return {
        "status": "FINALIZATION_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "finalization_stop_conditions_does_not_execute": True,
    }

"""Phase39: authorization stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_authorization_stop_conditions(authorization_package: dict[str, Any]) -> dict[str, Any]:
    if authorization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_authorization_package"}
    return {
        "status": "AUTHORIZATION_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "authorization_stop_conditions_does_not_execute": True,
    }

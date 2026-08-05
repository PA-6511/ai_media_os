"""Phase39: authorization controls builder."""
from __future__ import annotations

from typing import Any


def build_authorization_controls(authorization_package: dict[str, Any]) -> dict[str, Any]:
    if authorization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_authorization_package"}
    return {
        "status": "AUTHORIZATION_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "authorization_controls_does_not_execute": True,
    }

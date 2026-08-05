"""Phase38: confirmation controls builder."""
from __future__ import annotations

from typing import Any


def build_confirmation_controls(confirmation_package: dict[str, Any]) -> dict[str, Any]:
    if confirmation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_confirmation_package"}
    return {
        "status": "CONFIRMATION_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "confirmation_controls_does_not_execute": True,
    }

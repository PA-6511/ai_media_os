"""Phase40: validation controls builder."""
from __future__ import annotations

from typing import Any


def build_validation_controls(validation_package: dict[str, Any]) -> dict[str, Any]:
    if validation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_validation_package"}
    return {
        "status": "VALIDATION_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "validation_controls_does_not_execute": True,
    }

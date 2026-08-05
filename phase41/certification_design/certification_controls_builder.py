"""Phase41: certification controls builder."""
from __future__ import annotations

from typing import Any


def build_certification_controls(certification_package: dict[str, Any]) -> dict[str, Any]:
    if certification_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_certification_package"}
    return {
        "status": "CERTIFICATION_CONTROLS_READY",
        "single_file_scope_required": True,
        "sandbox_scope_required": True,
        "certification_controls_does_not_execute": True,
    }

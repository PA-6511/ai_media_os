"""Phase41: certification stop conditions builder."""
from __future__ import annotations

from typing import Any


def build_certification_stop_conditions(certification_package: dict[str, Any]) -> dict[str, Any]:
    if certification_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_certification_package"}
    return {
        "status": "CERTIFICATION_STOP_CONDITIONS_READY",
        "stop_on_scope_violation": True,
        "stop_on_sandbox_violation": True,
        "certification_stop_conditions_does_not_execute": True,
    }

"""Phase37: trigger evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_trigger_evidence_requirements(trigger_package: dict[str, Any]) -> dict[str, Any]:
    if trigger_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_trigger_package"}
    return {
        "status": "TRIGGER_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "trigger_evidence_does_not_execute": True,
    }

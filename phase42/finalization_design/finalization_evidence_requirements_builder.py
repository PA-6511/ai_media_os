"""Phase42: finalization evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_finalization_evidence_requirements(finalization_package: dict[str, Any]) -> dict[str, Any]:
    if finalization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_finalization_package"}
    return {
        "status": "FINALIZATION_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "finalization_evidence_does_not_execute": True,
    }

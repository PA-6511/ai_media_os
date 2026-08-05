"""Phase38: confirmation evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_confirmation_evidence_requirements(confirmation_package: dict[str, Any]) -> dict[str, Any]:
    if confirmation_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_confirmation_package"}
    return {
        "status": "CONFIRMATION_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "confirmation_evidence_does_not_execute": True,
    }

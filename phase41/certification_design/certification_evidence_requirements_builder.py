"""Phase41: certification evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_certification_evidence_requirements(certification_package: dict[str, Any]) -> dict[str, Any]:
    if certification_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_certification_package"}
    return {
        "status": "CERTIFICATION_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "certification_evidence_does_not_execute": True,
    }

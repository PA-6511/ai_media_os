"""Phase39: authorization evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_authorization_evidence_requirements(authorization_package: dict[str, Any]) -> dict[str, Any]:
    if authorization_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_authorization_package"}
    return {
        "status": "AUTHORIZATION_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "authorization_evidence_does_not_execute": True,
    }

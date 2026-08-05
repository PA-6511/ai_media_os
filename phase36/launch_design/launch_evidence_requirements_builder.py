"""Phase36: launch evidence requirements builder."""
from __future__ import annotations

from typing import Any


def build_launch_evidence_requirements(launch_package: dict[str, Any]) -> dict[str, Any]:
    if launch_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY":
        return {"status": "FAIL", "reason": "invalid_launch_package"}
    return {
        "status": "LAUNCH_EVIDENCE_REQUIREMENTS_READY",
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "launch_evidence_does_not_execute": True,
    }

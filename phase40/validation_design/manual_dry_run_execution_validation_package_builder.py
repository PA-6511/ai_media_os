"""Phase40: manual dry-run execution validation package builder.

Accepts Phase39's READY_FOR_PHASE40_PLANNING_ONLY result and produces a
validation package design.  Nothing is executed; this is design-only.
"""
from __future__ import annotations

from typing import Any


def build_manual_dry_run_execution_validation_package(
    phase39_result: dict[str, Any],
) -> dict[str, Any]:
    if phase39_result.get("readiness_status") != "READY_FOR_PHASE40_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase39_readiness_status_must_be_READY_FOR_PHASE40_PLANNING_ONLY",
        }
    if phase39_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase39_can_execute_must_be_false",
        }
    return {
        "status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
    }

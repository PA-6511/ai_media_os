"""Phase36: manual dry-run execution launch package builder.

Accepts Phase35's READY_FOR_PHASE36_PLANNING_ONLY result and produces a
launch package design.  Nothing is executed; this is design-only.
"""
from __future__ import annotations

from typing import Any


def build_manual_dry_run_execution_launch_package(
    phase35_result: dict[str, Any],
) -> dict[str, Any]:
    if phase35_result.get("readiness_status") != "READY_FOR_PHASE36_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase35_readiness_status_must_be_READY_FOR_PHASE36_PLANNING_ONLY",
        }
    if phase35_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase35_can_execute_must_be_false",
        }
    return {
        "status": "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
    }

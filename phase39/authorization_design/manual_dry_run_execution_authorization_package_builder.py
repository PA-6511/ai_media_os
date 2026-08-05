"""Phase39: manual dry-run execution authorization package builder.

Accepts Phase38's READY_FOR_PHASE39_PLANNING_ONLY result and produces an
authorization package design.  Nothing is executed; this is design-only.
"""
from __future__ import annotations

from typing import Any


def build_manual_dry_run_execution_authorization_package(
    phase38_result: dict[str, Any],
) -> dict[str, Any]:
    if phase38_result.get("readiness_status") != "READY_FOR_PHASE39_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase38_readiness_status_must_be_READY_FOR_PHASE39_PLANNING_ONLY",
        }
    if phase38_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase38_can_execute_must_be_false",
        }
    return {
        "status": "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "can_execute": False,
        "execute_allowed": False,
        "sandbox_scope_required": True,
    }

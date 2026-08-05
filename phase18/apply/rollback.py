from __future__ import annotations


def build_rollback_plan(execution_result: dict) -> dict:
    return {
        "status": "ROLLBACK_PLAN_READY",
        "restore_targets": execution_result.get("applied_files", []),
        "source_execution_status": execution_result.get("status"),
    }


def rollback_execution(rollback_plan: dict, dry_run: bool = True) -> dict:
    restore_targets = rollback_plan.get("restore_targets", [])
    if dry_run:
        return {
            "status": "WOULD_ROLLBACK",
            "restored": [],
            "planned_restore_targets": restore_targets,
        }

    return {
        "status": "SKIPPED",
        "restored": [],
        "planned_restore_targets": restore_targets,
    }

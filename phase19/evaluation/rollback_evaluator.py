from __future__ import annotations


def evaluate_rollback_readiness(rollback_plan: dict) -> dict:
    if not rollback_plan:
        return {
            "rollback_status": "FAIL",
            "findings": ["rollback_plan_missing"],
        }

    if rollback_plan.get("dry_run") is not True:
        return {
            "rollback_status": "FAIL",
            "findings": ["rollback_plan_not_dry_run"],
        }

    rollback_targets = rollback_plan.get("rollback_targets")
    if rollback_targets is None:
        return {
            "rollback_status": "FAIL",
            "findings": ["rollback_targets_missing"],
        }

    if len(rollback_targets) == 0:
        return {
            "rollback_status": "WARN",
            "findings": ["rollback_targets_empty"],
        }

    return {
        "rollback_status": "PASS",
        "findings": [f"rollback_targets_count={len(rollback_targets)}"],
    }

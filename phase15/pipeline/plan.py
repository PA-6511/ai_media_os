from __future__ import annotations


def build_plan(task_name: str, target_scope: str) -> dict:
    """Build a minimal, explicit plan object for phase15 DRY_RUN execution."""
    return {
        "phase": "15",
        "mode": "DRY_RUN",
        "task_name": task_name,
        "target_scope": target_scope,
        "human_approval_required": True,
    }

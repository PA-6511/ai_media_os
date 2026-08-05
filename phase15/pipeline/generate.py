from __future__ import annotations


def build_generation_prompt(plan: dict) -> str:
    """Build a constrained generation prompt from the phase15 plan."""
    task_name = plan.get("task_name", "unknown-task")
    target_scope = plan.get("target_scope", "phase15/")
    phase = plan.get("phase", "15")
    mode = plan.get("mode", "DRY_RUN")

    lines = [
        f"Phase {phase} generation task: {task_name}",
        f"Target scope: {target_scope}",
        f"Mode: {mode}",
        "Constraints:",
        "- Existing core logic must not be modified.",
        "- Changes must follow the allowlist only.",
        "- Delete operations are forbidden.",
        "- Keep execution DRY_RUN-first.",
    ]
    return "\n".join(lines)

from __future__ import annotations

from pathlib import Path

from phase18.workspace.path_guard import is_allowed_path, is_within_sandbox

_ALLOWED_OPERATIONS = {"create", "update"}


def _gate_passed(approval_result: dict) -> bool:
    return (
        approval_result.get("decision") == "APPROVE"
        and approval_result.get("status") == "PASS"
        and approval_result.get("gate_status") == "PASS_APPROVED"
        and approval_result.get("can_proceed") is True
    )


def execute_apply_plan(apply_plan: dict, approval_result: dict) -> dict:
    if not _gate_passed(approval_result):
        return {
            "status": "SKIPPED",
            "applied_files": [],
            "blocked_files": [],
            "can_promote_to_next": False,
            "reason": "approval_gate_not_passed",
        }

    if apply_plan.get("status") != "READY_TO_APPLY_DRY_RUN":
        return {
            "status": "FAIL",
            "applied_files": [],
            "blocked_files": [],
            "can_promote_to_next": False,
            "reason": "apply_plan_not_ready",
        }

    sandbox_root = str(apply_plan.get("sandbox_root", ""))
    allowlist_root = str(apply_plan.get("allowlist_root", ""))

    if not is_within_sandbox(allowlist_root, sandbox_root):
        return {
            "status": "POLICY_VIOLATION",
            "applied_files": [],
            "blocked_files": [],
            "can_promote_to_next": False,
            "reason": "allowlist_root_outside_sandbox",
        }

    applied_files: list[str] = []
    blocked_files: list[str] = []

    for change in apply_plan.get("planned_changes", []):
        target_path = str(change.get("target_path", ""))
        content = str(change.get("content", ""))
        operation = str(change.get("operation", "")).lower()

        if operation not in _ALLOWED_OPERATIONS:
            blocked_files.append(target_path)
            return {
                "status": "POLICY_VIOLATION",
                "applied_files": applied_files,
                "blocked_files": blocked_files,
                "can_promote_to_next": False,
                "reason": "delete_or_unknown_operation_not_allowed",
            }

        resolved_target = str(Path(target_path).resolve())

        if not is_within_sandbox(resolved_target, sandbox_root):
            blocked_files.append(resolved_target)
            return {
                "status": "POLICY_VIOLATION",
                "applied_files": applied_files,
                "blocked_files": blocked_files,
                "can_promote_to_next": False,
                "reason": "target_outside_sandbox",
            }

        if not is_allowed_path(resolved_target, allowlist_root):
            blocked_files.append(resolved_target)
            return {
                "status": "POLICY_VIOLATION",
                "applied_files": applied_files,
                "blocked_files": blocked_files,
                "can_promote_to_next": False,
                "reason": "target_outside_allowlist",
            }

        # Phase18 is DRY_RUN-only; we record intended writes without filesystem apply.
        _ = content
        applied_files.append(resolved_target)

    return {
        "status": "PASS",
        "applied_files": applied_files,
        "blocked_files": blocked_files,
        "can_promote_to_next": True,
        "reason": "sandbox_dry_run_apply_simulated",
    }

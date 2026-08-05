from __future__ import annotations

from pathlib import Path

from phase18.workspace.path_guard import is_within_sandbox

_ALLOWED_OPERATIONS = {"create", "update"}


def _derive_planned_changes(comparison_result: dict, selected_candidate_id: str) -> list[dict]:
    planned = comparison_result.get("planned_changes")
    if isinstance(planned, list) and planned:
        return planned

    for item in comparison_result.get("candidates_report", []):
        candidate = item.get("candidate", {}) if isinstance(item, dict) else {}
        if candidate.get("candidate_id") == selected_candidate_id:
            changes: list[dict] = []
            for changed in candidate.get("changed_files", []):
                changes.append(
                    {
                        "target_path": str(changed),
                        "content": f"DRY_RUN placeholder for {selected_candidate_id}",
                        "operation": "update",
                    }
                )
            return changes

    return []


def build_apply_plan(decision_package: dict, sandbox_root: str, allowlist_root: str) -> dict:
    selected_candidate_id = decision_package.get("selected_candidate_id")

    if decision_package.get("status") != "READY_FOR_HUMAN_REVIEW":
        return {"status": "FAIL", "reason": "decision_package_not_ready"}

    if not selected_candidate_id:
        return {"status": "FAIL", "reason": "selected_candidate_id_missing"}

    if not is_within_sandbox(allowlist_root, sandbox_root):
        return {
            "status": "POLICY_VIOLATION",
            "reason": "allowlist_root_outside_sandbox",
        }

    comparison_result = decision_package.get("comparison_result", {})
    planned_changes = _derive_planned_changes(comparison_result, selected_candidate_id)

    for change in planned_changes:
        if not all(key in change for key in ("target_path", "content", "operation")):
            return {"status": "FAIL", "reason": "invalid_planned_change_schema"}

        if str(change.get("operation", "")).lower() not in _ALLOWED_OPERATIONS:
            return {
                "status": "POLICY_VIOLATION",
                "reason": "operation_not_allowed",
            }

    return {
        "phase": "18",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "selected_candidate_id": selected_candidate_id,
        "planned_changes": planned_changes,
        "apply_scope": "sandbox_only",
        "sandbox_root": str(Path(sandbox_root).resolve()),
        "allowlist_root": str(Path(allowlist_root).resolve()),
        "status": "READY_TO_APPLY_DRY_RUN",
    }

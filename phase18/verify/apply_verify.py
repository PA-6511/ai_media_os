from __future__ import annotations

from phase18.workspace.path_guard import is_within_sandbox


def verify_apply_result(execution_result: dict, sandbox_root: str) -> dict:
    findings: list[str] = []
    verify_status = "PASS"

    outside_files = [
        path
        for path in execution_result.get("applied_files", [])
        if not is_within_sandbox(str(path), sandbox_root)
    ]

    if outside_files:
        verify_status = "FAIL"
        findings.append("applied_files_outside_sandbox_detected")

    if execution_result.get("blocked_files"):
        if verify_status != "FAIL":
            verify_status = "WARN"
        findings.append("blocked_files_recorded")

    can_promote_to_next = verify_status == "PASS" and execution_result.get("status") == "PASS"
    if not can_promote_to_next:
        findings.append("cannot_promote_to_next_stage")

    return {
        "verify_status": verify_status,
        "findings": findings,
        "can_promote_to_next": can_promote_to_next,
    }

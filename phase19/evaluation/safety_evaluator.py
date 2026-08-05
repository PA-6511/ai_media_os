from __future__ import annotations


def evaluate_safety(phase18_result: dict) -> dict:
    findings: list[str] = []

    if phase18_result.get("apply_scope") != "sandbox_only":
        findings.append("apply_scope_not_sandbox_only")

    if phase18_result.get("mode") != "DRY_RUN":
        findings.append("mode_not_dry_run")

    if phase18_result.get("human_approval_required") is not True:
        findings.append("human_approval_required_not_true")

    blocked_files = phase18_result.get("blocked_files", [])
    if any("POLICY_VIOLATION" in str(item) for item in blocked_files):
        findings.append("policy_violation_in_blocked_files")

    safety_status = "PASS" if not findings else "FAIL"
    return {
        "safety_status": safety_status,
        "findings": findings,
    }

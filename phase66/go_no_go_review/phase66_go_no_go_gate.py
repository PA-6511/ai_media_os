from __future__ import annotations


REQUIRED_SAFETY_FLAGS = {
    "dry_run_fixed": True,
    "human_approval_required": True,
    "can_execute": False,
    "execute_allowed": False,
    "max_files_to_execute": 1,
    "sandbox_scope_required": True,
    "single_file_scope_required": True,
    "does_not_execute_guards": True,
}


ALLOWED_DECISIONS = {"ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY", "NO_GO"}


def judge_phase66_go_no_go(
    phase65_completion_report: dict,
    selected_decision: str | None = None,
) -> dict:
    reasons: list[str] = []

    if phase65_completion_report.get("completion_status") != "PASS":
        reasons.append("phase65 completion_status must be PASS")

    safety = phase65_completion_report.get("safety_boundaries")
    if not isinstance(safety, dict):
        reasons.append("phase65 safety_boundaries must be a dict")
    else:
        for key, expected in REQUIRED_SAFETY_FLAGS.items():
            if safety.get(key) != expected:
                reasons.append(f"phase65 safety_boundaries.{key} must be {expected}")

    if selected_decision not in ALLOWED_DECISIONS:
        reasons.append("selected_decision must be ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY or NO_GO")

    if reasons:
        return {
            "review_status": "NOT_APPROVED",
            "go_no_go": "NO_GO",
            "can_execute": False,
            "execute_allowed": False,
            "next_step": "fix_findings_and_repeat_phase66_review",
            "reasons": reasons,
        }

    if selected_decision == "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY":
        return {
            "review_status": "APPROVED",
            "go_no_go": "GO",
            "can_execute": False,
            "execute_allowed": False,
            "next_step": "prepare_limited_dry_run_protocol_without_execution",
            "reasons": [],
        }

    return {
        "review_status": "APPROVED",
        "go_no_go": "NO_GO",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "hold_and_monitor_without_execution",
        "reasons": [],
    }

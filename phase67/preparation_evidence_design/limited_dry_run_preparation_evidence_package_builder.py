from __future__ import annotations


def build_limited_dry_run_preparation_evidence_package(phase66_report: dict) -> dict:
    if phase66_report.get("review_status") != "APPROVED":
        return {"status": "FAIL", "reason": "phase66_review_status_not_approved"}
    if phase66_report.get("go_no_go") != "GO":
        return {"status": "FAIL", "reason": "phase66_go_no_go_must_be_go"}
    if (
        phase66_report.get("selected_decision")
        != "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY"
    ):
        return {"status": "FAIL", "reason": "phase66_selected_decision_not_met"}
    if phase66_report.get("can_execute") is not False:
        return {"status": "FAIL", "reason": "phase66_can_execute_must_be_false"}
    if phase66_report.get("execute_allowed") is not False:
        return {"status": "FAIL", "reason": "phase66_execute_allowed_must_be_false"}

    return {
        "phase": 67,
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "package_scope": "limited_dry_run_preparation_evidence_package_design_only",
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "status": "PREPARATION_EVIDENCE_PACKAGE_READY",
        "next_step": "build_preparation_controls",
    }

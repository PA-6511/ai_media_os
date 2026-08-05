from __future__ import annotations


def judge_approval_gate(approval_result: dict) -> dict:
    decision = approval_result.get("decision")
    status = approval_result.get("status")

    if decision == "APPROVE" and status == "PASS":
        return {
            "gate_status": "PASS_APPROVED",
            "can_proceed": True,
            "next_step": "phase18_dry_run_workspace_only",
        }

    if decision == "REJECT":
        return {
            "gate_status": "FAIL_REJECTED",
            "can_proceed": False,
            "next_step": "stop_pipeline",
        }

    if decision == "NEEDS_REVISION":
        return {
            "gate_status": "WARN_NEEDS_REVISION",
            "can_proceed": False,
            "next_step": "return_to_phase16_candidate_generation",
        }

    if decision == "PENDING":
        return {
            "gate_status": "WARN_PENDING_REVIEW",
            "can_proceed": False,
            "next_step": "wait_for_human_review",
        }

    return {
        "gate_status": "FAIL_INVALID_APPROVAL",
        "can_proceed": False,
        "next_step": "fix_approval_file",
    }

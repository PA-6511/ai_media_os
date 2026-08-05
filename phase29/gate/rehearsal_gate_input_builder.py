from __future__ import annotations


def build_rehearsal_gate_input(phase28_result: dict) -> dict:
    if phase28_result.get("readiness_status") != "READY_FOR_PHASE29_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase28_not_ready_for_phase29_planning_only",
        }

    if phase28_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase28_can_execute_must_be_false",
        }

    return {
        "phase": "29",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "gate_scope": "manual_dry_run_rehearsal_gate_design_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "status": "REHEARSAL_GATE_INPUT_READY",
        "next_step": "build_checklist_and_evidence_gate",
    }

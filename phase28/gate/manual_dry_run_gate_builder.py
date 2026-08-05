from __future__ import annotations


def build_manual_dry_run_gate(phase27_result: dict) -> dict:
    if phase27_result.get("readiness_status") != "READY_FOR_PHASE28_PLANNING_ONLY":
        return {
            "status": "FAIL",
            "reason": "phase27_not_ready_for_phase28_planning_only",
        }

    if phase27_result.get("can_execute") is not False:
        return {
            "status": "FAIL",
            "reason": "phase27_can_execute_must_be_false",
        }

    return {
        "phase": "28",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "gate_scope": "manual_single_file_dry_run_gate_design_only",
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "gate_required": True,
        "status": "MANUAL_DRY_RUN_GATE_READY",
        "next_step": "define_approval_input_and_evidence_spec",
    }

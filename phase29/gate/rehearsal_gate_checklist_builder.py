from __future__ import annotations


def build_rehearsal_gate_checklist(gate_input: dict) -> dict:
    if gate_input.get("status") != "REHEARSAL_GATE_INPUT_READY":
        return {
            "status": "FAIL",
            "reason": "gate_input_not_ready",
        }

    return {
        "checklist_required": True,
        "checklist_items": [
            "confirm_single_file_scope",
            "confirm_dry_run_mode",
            "confirm_manual_approval_present",
            "confirm_no_delete_instruction",
            "confirm_no_production_target",
            "confirm_policy_snapshot_attached",
        ],
        "checklist_does_not_execute": True,
        "status": "REHEARSAL_GATE_CHECKLIST_READY",
    }

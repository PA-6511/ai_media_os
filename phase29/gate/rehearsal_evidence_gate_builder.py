from __future__ import annotations


def build_rehearsal_evidence_gate(gate_input: dict) -> dict:
    if gate_input.get("status") != "REHEARSAL_GATE_INPUT_READY":
        return {
            "status": "FAIL",
            "reason": "gate_input_not_ready",
        }

    return {
        "evidence_gate_required": True,
        "evidence_fields": [
            "request_id",
            "approver",
            "target_file",
            "checklist_status",
            "policy_status",
            "notes",
            "created_at",
        ],
        "evidence_does_not_execute": True,
        "status": "REHEARSAL_EVIDENCE_GATE_READY",
    }

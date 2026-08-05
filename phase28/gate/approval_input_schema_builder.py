from __future__ import annotations


def build_approval_input_schema(gate: dict) -> dict:
    if gate.get("status") != "MANUAL_DRY_RUN_GATE_READY":
        return {
            "status": "FAIL",
            "reason": "gate_not_ready",
        }

    return {
        "approval_required": True,
        "allowed_decisions": [
            "ALLOW_PHASE29_PLANNING_ONLY",
            "REJECT",
            "NEEDS_REVISION",
        ],
        "required_fields": [
            "request_id",
            "target_file",
            "approver",
            "rationale",
            "policy_snapshot",
            "timestamp",
        ],
        "allow_does_not_execute": True,
        "status": "APPROVAL_INPUT_SCHEMA_READY",
    }

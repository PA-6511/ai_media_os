from __future__ import annotations


def build_evidence_storage_spec(gate: dict) -> dict:
    if gate.get("status") != "MANUAL_DRY_RUN_GATE_READY":
        return {
            "status": "FAIL",
            "reason": "gate_not_ready",
        }

    return {
        "evidence_required": True,
        "evidence_does_not_execute": True,
        "storage_fields": [
            "request_id",
            "decision",
            "approver",
            "target_file",
            "policy_result",
            "checklist_result",
            "notes",
            "created_at",
        ],
        "retention_note": "planning_stage_only_no_execution",
        "status": "EVIDENCE_STORAGE_SPEC_READY",
    }

from __future__ import annotations


def build_stop_conditions(plan: dict) -> dict:
    _ = plan
    return {
        "status": "STOP_CONDITIONS_READY",
        "conditions": [
            "target_files_count_exceeds_1",
            "manual_approval_missing",
            "policy_violation_detected",
            "dry_run_disabled",
            "any_delete_instruction_detected",
            "any_production_instruction_detected",
        ],
    }

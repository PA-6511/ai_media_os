from __future__ import annotations


def build_abort_conditions(procedure: dict) -> dict:
    _ = procedure
    return {
        "status": "ABORT_CONDITIONS_READY",
        "conditions": [
            "more_than_one_file_detected",
            "dry_run_flag_missing",
            "manual_approval_missing",
            "delete_instruction_detected",
            "production_path_detected",
            "unexpected_policy_violation",
        ],
    }

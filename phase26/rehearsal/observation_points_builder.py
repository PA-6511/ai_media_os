from __future__ import annotations


def build_observation_points(procedure: dict) -> dict:
    _ = procedure
    return {
        "status": "OBSERVATION_POINTS_READY",
        "points": [
            "target_file_before_state",
            "target_file_after_state_placeholder",
            "dry_run_log_capture",
            "manual_approval_reference",
            "policy_check_result",
            "stop_condition_status",
        ],
    }

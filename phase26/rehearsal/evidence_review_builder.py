from __future__ import annotations


def build_evidence_review(observation_points: dict) -> dict:
    _ = observation_points
    return {
        "evidence_review_required": True,
        "evidence_does_not_execute": True,
        "required_evidence_checks": [
            "before_after_state_template_present",
            "dry_run_log_format_defined",
            "manual_approval_reference_present",
            "policy_check_capture_present",
        ],
        "status": "EVIDENCE_REVIEW_READY",
    }

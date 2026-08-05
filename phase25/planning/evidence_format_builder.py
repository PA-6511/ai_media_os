from __future__ import annotations


def build_evidence_format(plan: dict) -> dict:
    _ = plan
    return {
        "evidence_required": True,
        "evidence_fields": [
            "target_file",
            "planned_action",
            "dry_run_mode",
            "manual_approval_reference",
            "stop_condition_status",
            "expected_outcome",
            "observed_result_placeholder",
        ],
        "evidence_does_not_execute": True,
        "status": "EVIDENCE_FORMAT_READY",
    }

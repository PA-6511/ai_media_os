from __future__ import annotations


def build_evidence_requirements(control_design: dict) -> dict:
    if control_design.get("status") != "PRE_EXECUTION_CONTROL_DESIGN_READY":
        return {
            "status": "FAIL",
            "reason": "pre_execution_control_design_not_ready",
        }

    return {
        "evidence_required": True,
        "required_artifacts": [
            "target_file_path",
            "sandbox_proof",
            "manual_approval_record",
            "dry_run_trace",
            "policy_evaluation_result",
        ],
        "missing_evidence_blocks_progress": True,
        "evidence_does_not_execute": True,
        "status": "EVIDENCE_REQUIREMENTS_READY",
    }

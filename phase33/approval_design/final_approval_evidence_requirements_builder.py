from __future__ import annotations


def build_final_approval_evidence_requirements(approval_package: dict) -> dict:
    if (
        approval_package.get("status")
        != "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"
    ):
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_approval_package_not_ready",
        }

    return {
        "evidence_required": True,
        "required_artifacts": [
            "target_file_path",
            "sandbox_proof",
            "manual_approval_record",
            "final_approval_controls_snapshot",
            "final_approval_stop_conditions_snapshot",
            "policy_evaluation_result",
        ],
        "missing_evidence_blocks_progress": True,
        "final_approval_evidence_does_not_execute": True,
        "status": "FINAL_APPROVAL_EVIDENCE_REQUIREMENTS_READY",
    }

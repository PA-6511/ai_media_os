from __future__ import annotations


def build_readiness_evidence_requirements(readiness_package: dict) -> dict:
    if readiness_package.get("status") != "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY":
        return {
            "status": "FAIL",
            "reason": "manual_dry_run_execution_readiness_package_not_ready",
        }

    return {
        "evidence_required": True,
        "required_artifacts": [
            "target_file_path",
            "sandbox_proof",
            "manual_approval_record",
            "readiness_controls_snapshot",
            "readiness_stop_conditions_snapshot",
            "policy_evaluation_result",
        ],
        "missing_evidence_blocks_progress": True,
        "readiness_evidence_does_not_execute": True,
        "status": "READINESS_EVIDENCE_REQUIREMENTS_READY",
    }
